import { NextResponse } from "next/server";
import Stripe from "stripe";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";

export async function POST() {
  const session = await getServerSession(authOptions);
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const stripeKey = process.env.STRIPE_SECRET_KEY;
  const priceId = process.env.STRIPE_PRO_PRICE_ID;

  if (!stripeKey || !priceId) {
    return NextResponse.json(
      { error: "Stripe is not configured. Contact support." },
      { status: 503 },
    );
  }

  const stripe = new Stripe(stripeKey, { apiVersion: "2026-03-25.dahlia" });

  const appBase = process.env.NEXTAUTH_URL || "https://app.aletheia-core.com";

  const checkoutSession = await stripe.checkout.sessions.create({
    mode: "subscription",
    payment_method_types: ["card"],
    line_items: [{ price: priceId, quantity: 1 }],
    success_url: `${appBase}/dashboard?upgraded=true`,
    cancel_url: `${appBase}/dashboard?upgrade=cancelled`,
    client_reference_id: session.user.id,
    metadata: { userId: session.user.id },
    customer_email: session.user.email ?? undefined,
  });

  return NextResponse.json({ url: checkoutSession.url });
}
