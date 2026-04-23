import { NextResponse } from "next/server";
import { headers } from "next/headers";
import crypto from "crypto";
import prisma from "@/lib/prisma";

/**
 * Stripe webhook handler with HMAC signature verification.
 * Uses Stripe's v1 signature scheme (HMAC-SHA256) without requiring the Stripe SDK.
 * STRIPE_WEBHOOK_SECRET must be set in production (whsec_...).
 */

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
      // Use client_reference_id (set server-side in checkout creation) — NOT metadata
      // which could be tampered with by intercepting the checkout URL.
      const userId = session.client_reference_id;

      // Verify price matches expected amount to prevent price manipulation
      const expectedAmount = parseInt(process.env.STRIPE_PRO_PRICE_AMOUNT || "4900", 10);
      const expectedCurrency = (process.env.STRIPE_PRO_CURRENCY || "usd").toLowerCase();
      const sessionAmount = session.amount_total as number | undefined;
      const sessionCurrency = (session.currency as string | undefined)?.toLowerCase();

      if (
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
        await prisma.user.update({
          where: { id: userId },
          data: {
            plan: "PRO",
            stripeCustomerId: session.customer as string | undefined,
            stripeSubscriptionId: session.subscription as string | undefined,
          },
        });
      }
      break;
    }

    case "customer.subscription.deleted": {
      const subscription = event.data.object;
      const customerId = subscription.customer as string;
      if (customerId) {
        await prisma.user.updateMany({
          where: { stripeCustomerId: customerId },
          data: { plan: "TRIAL" },
        });
      }
      break;
    }

    case "customer.subscription.updated": {
      const subscription = event.data.object;
      const customerId = subscription.customer as string;
      const status = subscription.status as string;
      if (customerId && status === "active") {
        await prisma.user.updateMany({
          where: { stripeCustomerId: customerId },
          data: { plan: "PRO" },
        });
      }
      break;
    }

    default:
      // Unhandled event type — acknowledge receipt
      break;
  }

  return NextResponse.json({ received: true });
}
