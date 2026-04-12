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
      { error: "Stripe webhook not configured" },
      { status: 503 },
    );
  }

  const body = await request.text();
  const sig = headers().get("stripe-signature");
  if (!sig) {
    return NextResponse.json(
      { error: "Missing stripe-signature header" },
      { status: 400 },
    );
  }

  // Verify signature — reject unsigned or tampered events
  if (!verifyStripeSignature(body, sig, secret)) {
    return NextResponse.json(
      { error: "Invalid signature" },
      { status: 400 },
    );
  }

  let event: { type: string; data: { object: Record<string, unknown> } };
  try {
    event = JSON.parse(body);
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  switch (event.type) {
    case "checkout.session.completed": {
      const session = event.data.object;
      const userId = session.metadata && (session.metadata as Record<string, string>).userId;
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
