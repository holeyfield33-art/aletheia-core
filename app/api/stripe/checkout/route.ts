import { NextResponse } from "next/server";
import Stripe from "stripe";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { getBaseUrl } from "@/lib/auth-config";
import { PRICING } from "@/lib/site-config";

type CheckoutTier = "scale" | "pro" | "payg";
type CheckoutSelection = CheckoutTier | "enterprise";

function normalizeTier(rawTier: string | null | undefined): CheckoutSelection {
  if (rawTier === "enterprise") return "enterprise";
  if (rawTier === "payg") return "payg";
  if (rawTier === "pro") return "pro";
  return "scale";
}

function getPriceIdForTier(tier: CheckoutTier): string | undefined {
  if (tier === "scale") return PRICING.scale.stripePriceId;
  if (tier === "pro") return PRICING.pro.stripePriceId;
  return PRICING.payg.stripePriceId;
}

function getInternalPlanForTier(tier: CheckoutTier): "PRO" | "MAX" | "ENTERPRISE" {
  if (tier === "scale") return "PRO";
  if (tier === "pro") return "MAX";
  return "ENTERPRISE";
}

function isSameOriginBrowserRequest(request: Request, url: URL): boolean {
  const secFetchSite = request.headers.get("sec-fetch-site");
  if (secFetchSite === "cross-site") return false;
  if (secFetchSite === "same-origin" || secFetchSite === "same-site" || secFetchSite === "none") {
    return true;
  }

  const origin = request.headers.get("origin");
  if (origin) {
    try {
      return new URL(origin).host === url.host;
    } catch {
      return false;
    }
  }

  const referer = request.headers.get("referer");
  if (referer) {
    try {
      return new URL(referer).host === url.host;
    } catch {
      return false;
    }
  }

  // Non-browser clients should not trigger checkout creation.
  return false;
}

async function createCheckoutResponse(request: Request, redirectToStripe: boolean) {
  const url = new URL(request.url);
  if (!isSameOriginBrowserRequest(request, url)) {
    return NextResponse.json({ error: "forbidden" }, { status: 403 });
  }

  const session = await getServerSession(authOptions);
  if (!session?.user?.id) {
    if (redirectToStripe) {
      const loginUrl = new URL("/auth/login", url.origin);
      loginUrl.searchParams.set("callbackUrl", `${url.pathname}${url.search}`);
      return NextResponse.redirect(loginUrl);
    }
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  let body: { tier?: string } = {};
  try {
    body = await request.json();
  } catch {
    body = {};
  }

  const selectedTier = normalizeTier(url.searchParams.get("tier") ?? body.tier);
  if (selectedTier === "enterprise") {
    const contactUrl = new URL("/contact", url.origin);
    if (redirectToStripe) {
      return NextResponse.redirect(contactUrl);
    }
    return NextResponse.json({ url: contactUrl.toString() });
  }

  const internalPlan = getInternalPlanForTier(selectedTier);

  const stripeKey = process.env.STRIPE_SECRET_KEY;
  const priceId = getPriceIdForTier(selectedTier);

  if (!stripeKey || !priceId) {
    return NextResponse.json(
      { error: "configuration_error" },
      { status: 503 },
    );
  }

  const stripe = new Stripe(stripeKey, { apiVersion: "2026-03-25.dahlia" });

  const appBase = getBaseUrl();
  const lineItems =
    selectedTier === "payg"
      ? [{ price: priceId }]
      : [{ price: priceId, quantity: 1 }];

  let checkoutSession: Stripe.Checkout.Session;
  try {
    checkoutSession = await stripe.checkout.sessions.create({
      mode: "subscription",
      payment_method_types: ["card"],
      line_items: lineItems,
      success_url: `${appBase}/dashboard?upgraded=true`,
      cancel_url: `${appBase}/dashboard?upgrade=cancelled`,
      client_reference_id: session.user.id,
      metadata: {
        userId: session.user.id,
        tier: selectedTier,
        plan: internalPlan,
        billingModel: selectedTier === "payg" ? "metered" : "licensed",
      },
      subscription_data: {
        metadata: {
          userId: session.user.id,
          tier: selectedTier,
        },
      },
      customer_email: session.user.email ?? undefined,
    });
  } catch (error) {
    console.error("[stripe-checkout] Failed to create checkout session", error);
    return NextResponse.json({ error: "checkout_session_failed" }, { status: 500 });
  }

  if (redirectToStripe && checkoutSession.url) {
    return NextResponse.redirect(checkoutSession.url);
  }

  return NextResponse.json({ url: checkoutSession.url });
}

export async function GET(request: Request) {
  return createCheckoutResponse(request, true);
}

export async function POST(request: Request) {
  return createCheckoutResponse(request, false);
}
