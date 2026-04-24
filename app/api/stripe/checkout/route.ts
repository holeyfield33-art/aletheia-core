import { NextResponse } from "next/server";
import Stripe from "stripe";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { getBaseUrl } from "@/lib/auth-config";
import { getStripePriceIdForPlan, type HostedPlanId } from "@/lib/hosted-plans";

export async function POST(request: Request) {
  const session = await getServerSession(authOptions);
  if (!session?.user?.id) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  let body: { plan?: string } = {};
  try {
    body = await request.json();
  } catch {
    body = {};
  }

  const requestedPlan = body.plan?.toUpperCase();
  const selectedPlan: HostedPlanId = requestedPlan === "MAX" ? "MAX" : "PRO";

  const stripeKey = process.env.STRIPE_SECRET_KEY;
  const priceId = getStripePriceIdForPlan(selectedPlan);

  if (!stripeKey || !priceId) {
    return NextResponse.json(
      { error: "configuration_error" },
      { status: 503 },
    );
  }

  const stripe = new Stripe(stripeKey, { apiVersion: "2026-03-25.dahlia" });

  const appBase = getBaseUrl();

  const checkoutSession = await stripe.checkout.sessions.create({
    mode: "subscription",
    payment_method_types: ["card"],
    line_items: [{ price: priceId, quantity: 1 }],
    success_url: `${appBase}/dashboard?upgraded=true`,
    cancel_url: `${appBase}/dashboard?upgrade=cancelled`,
    client_reference_id: session.user.id,
    metadata: { userId: session.user.id, plan: selectedPlan },
    customer_email: session.user.email ?? undefined,
  });

  return NextResponse.json({ url: checkoutSession.url });
}
