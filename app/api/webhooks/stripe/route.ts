import { NextResponse } from "next/server";
import { headers } from "next/headers";
import crypto from "crypto";
import prisma from "@/lib/prisma";
import { getHostedPlanConfig, type HostedPlanId } from "@/lib/hosted-plans";
import { PRICING } from "@/lib/site-config";

/**
 * Stripe webhook handler with HMAC signature verification.
 * Uses Stripe's v1 signature scheme (HMAC-SHA256) without requiring the Stripe SDK.
 * STRIPE_WEBHOOK_SECRET must be set in production (whsec_...).
 */

type CheckoutTier = "scale" | "pro" | "payg";

const PAYG_MONTHLY_QUOTA = 2_147_483_647;

function normalizeTier(rawTier: string | null | undefined): CheckoutTier {
  if (rawTier === "payg") return "payg";
  if (rawTier === "pro") return "pro";
  return "scale";
}

function getPlanForTier(tier: CheckoutTier): HostedPlanId {
  if (tier === "scale") return "PRO";
  if (tier === "pro") return "MAX";
  return "ENTERPRISE";
}

function getStripePriceIdForTier(tier: CheckoutTier): string | undefined {
  if (tier === "scale") return PRICING.scale.stripePriceId;
  if (tier === "pro") return PRICING.pro.stripePriceId;
  return PRICING.payg.stripePriceId;
}

function getStripeExpectedAmountForTier(tier: CheckoutTier): number | undefined {
  if (tier === "scale") {
    return parseInt(process.env.STRIPE_SCALE_PRICE_AMOUNT || String(PRICING.scale.price * 100), 10);
  }
  if (tier === "pro") {
    return parseInt(process.env.STRIPE_PRO_PRICE_AMOUNT || String(PRICING.pro.price * 100), 10);
  }
  return undefined;
}

function getStripeCurrencyForTier(tier: CheckoutTier): string {
  if (tier === "scale") {
    return (process.env.STRIPE_SCALE_CURRENCY || process.env.STRIPE_PRO_CURRENCY || "usd").toLowerCase();
  }
  if (tier === "payg") {
    return (process.env.STRIPE_PAYG_CURRENCY || process.env.STRIPE_PRO_CURRENCY || "usd").toLowerCase();
  }
  return (process.env.STRIPE_PRO_CURRENCY || "usd").toLowerCase();
}

function getQuotaUpdateForPlan(plan: HostedPlanId): { plan: string; monthlyQuota: number } {
  if (plan === "ENTERPRISE") {
    return { plan: "enterprise", monthlyQuota: PAYG_MONTHLY_QUOTA };
  }

  const planConfig = getHostedPlanConfig(plan);
  return {
    plan: planConfig.apiKeyPlan,
    monthlyQuota: planConfig.monthlyCalls,
  };
}

function getTierForPriceId(priceId: string | undefined): CheckoutTier {
  if (priceId && priceId === PRICING.payg.stripePriceId) return "payg";
  if (priceId && priceId === PRICING.pro.stripePriceId) return "pro";
  return "scale";
}

function verifyStripeSignature(
  body: string,
  sigHeader: string,
  secret: string,
  toleranceSec = 300,
): boolean {
  // Parse Stripe signature header: t=timestamp,v1=signature
  const parts: Record<string, string> = {};
  for (const item of sigHeader.split(",")) {
    const [key, val] = item.split("=", 2);
    if (key && val) parts[key.trim()] = val.trim();
  }

  const timestamp = parts["t"];
  const v1Sig = parts["v1"];
  if (!timestamp || !v1Sig) return false;

  // Reject old timestamps to prevent replay attacks
  const ts = parseInt(timestamp, 10);
  if (isNaN(ts)) return false;
  const age = Math.abs(Math.floor(Date.now() / 1000) - ts);
  if (age > toleranceSec) return false;

  // Compute expected signature: HMAC-SHA256(secret, timestamp.body)
  const signedPayload = `${timestamp}.${body}`;
  const expected = crypto
    .createHmac("sha256", secret)
    .update(signedPayload, "utf8")
    .digest("hex");

  // Constant-time comparison to prevent timing attacks
  try {
    return crypto.timingSafeEqual(
      Buffer.from(v1Sig, "hex"),
      Buffer.from(expected, "hex"),
    );
  } catch {
    return false;
  }
}

export async function POST(request: Request) {
  const secret = process.env.STRIPE_WEBHOOK_SECRET;
  if (!secret) {
    return NextResponse.json(
      { error: "configuration_error" },
      { status: 503 },
    );
  }

  const body = await request.text();
  const requestHeaders = await headers();
  const sig = requestHeaders.get("stripe-signature");
  if (!sig) {
    return NextResponse.json(
      { error: "missing_signature" },
      { status: 400 },
    );
  }

  // Verify signature — reject unsigned or tampered events
  if (!verifyStripeSignature(body, sig, secret)) {
    return NextResponse.json(
      { error: "invalid_signature" },
      { status: 400 },
    );
  }

  let event: { type: string; data: { object: Record<string, unknown> } };
  try {
    event = JSON.parse(body);
  } catch {
    return NextResponse.json({ error: "invalid_json" }, { status: 400 });
  }

  switch (event.type) {
    case "checkout.session.completed": {
      const session = event.data.object;
      const sessionMetadata =
        typeof session.metadata === "object" && session.metadata !== null
          ? (session.metadata as Record<string, unknown>)
          : undefined;
      // Use client_reference_id (set server-side in checkout creation) — NOT metadata
      // which could be tampered with by intercepting the checkout URL.
      const userId = session.client_reference_id;

      const selectedTier = normalizeTier(
        typeof sessionMetadata?.tier === "string" ? sessionMetadata.tier : undefined,
      );
      const selectedPlan = getPlanForTier(selectedTier);
      const expectedAmount = getStripeExpectedAmountForTier(selectedTier);
      const expectedCurrency = getStripeCurrencyForTier(selectedTier);
      const expectedPriceId = getStripePriceIdForTier(selectedTier);
      const sessionAmount = session.amount_total as number | undefined;
      const sessionCurrency = (session.currency as string | undefined)?.toLowerCase();

      if (
        expectedAmount !== undefined &&
        sessionAmount !== undefined &&
        sessionCurrency !== undefined &&
        (sessionAmount !== expectedAmount || sessionCurrency !== expectedCurrency)
      ) {
        console.error(
          `[stripe-webhook] Price mismatch: expected ${expectedAmount} ${expectedCurrency}, got ${sessionAmount} ${sessionCurrency}`,
        );
        return NextResponse.json(
          { error: "price_mismatch", message: "No matching price found" },
          { status: 400 },
        );
      }

      if (userId && typeof userId === "string") {
        const quotaUpdate = getQuotaUpdateForPlan(selectedPlan);
        await prisma.user.update({
          where: { id: userId },
          data: {
            plan: selectedPlan,
            stripeCustomerId: session.customer as string | undefined,
            stripeSubscriptionId: session.subscription as string | undefined,
            stripePriceId: expectedPriceId,
          },
        });

        await prisma.apiKey.updateMany({
          where: { userId, status: "active" },
          data: {
            plan: quotaUpdate.plan,
            monthlyQuota: quotaUpdate.monthlyQuota,
          },
        });
      }
      break;
    }

    case "customer.subscription.deleted": {
      const subscription = event.data.object;
      const customerId = subscription.customer as string;
      if (customerId) {
        const trialPlan = getHostedPlanConfig("TRIAL");
        await prisma.user.updateMany({
          where: { stripeCustomerId: customerId },
          data: { plan: "TRIAL" },
        });
        const users = await prisma.user.findMany({
          where: { stripeCustomerId: customerId },
          select: { id: true },
        });
        if (users.length > 0) {
          await prisma.apiKey.updateMany({
            where: { userId: { in: users.map((user) => user.id) }, status: "active" },
            data: {
              plan: trialPlan.apiKeyPlan,
              monthlyQuota: trialPlan.monthlyCalls,
            },
          });
        }
      }
      break;
    }

    case "customer.subscription.updated": {
      const subscription = event.data.object;
      const subscriptionItems =
        typeof subscription.items === "object" && subscription.items !== null
          ? (subscription.items as { data?: Array<{ price?: { id?: string } }> })
          : undefined;
      const customerId = subscription.customer as string;
      const status = subscription.status as string;
      const priceId = subscriptionItems?.data?.[0]?.price?.id;
      const selectedTier = getTierForPriceId(priceId);
      const selectedPlan = getPlanForTier(selectedTier);
      if (customerId && status === "active") {
        const quotaUpdate = getQuotaUpdateForPlan(selectedPlan);
        await prisma.user.updateMany({
          where: { stripeCustomerId: customerId },
          data: { plan: selectedPlan, stripePriceId: priceId },
        });
        const users = await prisma.user.findMany({
          where: { stripeCustomerId: customerId },
          select: { id: true },
        });
        if (users.length > 0) {
          await prisma.apiKey.updateMany({
            where: { userId: { in: users.map((user) => user.id) }, status: "active" },
            data: {
              plan: quotaUpdate.plan,
              monthlyQuota: quotaUpdate.monthlyQuota,
            },
          });
        }
      }
      break;
    }

    default:
      // Unhandled event type — acknowledge receipt
      break;
  }

  return NextResponse.json({ received: true });
}
