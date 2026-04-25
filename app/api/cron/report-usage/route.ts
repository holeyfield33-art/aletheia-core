import { NextRequest, NextResponse } from "next/server";
import Stripe from "stripe";
import {
  clearUnreportedUsage,
  getStaleUnreportedEventCount,
  getUsersWithPendingUsage,
} from "@/lib/usage-tracking";

export const maxDuration = 60;

async function sendSlackAlert(message: string): Promise<void> {
  const webhookUrl = process.env.SLACK_WEBHOOK_URL;
  if (!webhookUrl) return;

  try {
    await fetch(webhookUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: message }),
    });
  } catch (error) {
    console.error("[usage-report] Failed to send Slack alert", { error });
  }
}

function getStripeClient(): Stripe | null {
  const stripeKey = process.env.STRIPE_SECRET_KEY;
  if (!stripeKey) return null;
  return new Stripe(stripeKey, { apiVersion: "2026-03-25.dahlia" });
}

export async function GET(request: NextRequest) {
  const auth = request.headers.get("authorization");
  const cronSecret = process.env.CRON_SECRET;

  if (!cronSecret || auth !== `Bearer ${cronSecret}`) {
    return new NextResponse("Unauthorized", { status: 401 });
  }

  const stripe = getStripeClient();
  const paygMeteredPriceId = process.env.STRIPE_PAYG_METERED_PRICE_ID;

  if (!stripe || !paygMeteredPriceId) {
    return NextResponse.json(
      { error: "configuration_error" },
      { status: 503 },
    );
  }

  const users = await getUsersWithPendingUsage();
  let reportedUsers = 0;
  let reportedUnits = 0;
  let failedUsers = 0;

  for (const user of users) {
    const pending = Number(user.pendingUsage);
    if (!user.stripeSubscriptionId || pending <= 0) continue;

    try {
      const subscription = await stripe.subscriptions.retrieve(
        user.stripeSubscriptionId,
        {
          expand: ["items.data.price"],
        },
      );

      const subscriptionItem = subscription.items.data.find(
        (item) => item.price?.id === paygMeteredPriceId,
      );

      if (!subscriptionItem) {
        failedUsers += 1;
        console.error(
          "[usage-report] Missing PAYG metered subscription item",
          { userId: user.userId, subscriptionId: user.stripeSubscriptionId },
        );
        continue;
      }

      // Stripe SDK typings can lag API support for usage-record endpoints.
      const subscriptionItemsCompat = stripe.subscriptionItems as unknown as {
        createUsageRecord: (
          id: string,
          params: {
            quantity: number;
            timestamp: number;
            action: "increment" | "set";
          },
        ) => Promise<unknown>;
      };

      await subscriptionItemsCompat.createUsageRecord(subscriptionItem.id, {
        quantity: pending,
        timestamp: Math.floor(Date.now() / 1000),
        action: "increment",
      });

      await clearUnreportedUsage(user.userId, pending);
      reportedUsers += 1;
      reportedUnits += pending;
    } catch (error) {
      failedUsers += 1;
      console.error("[usage-report] Failed to report usage", {
        userId: user.userId,
        pending,
        error,
      });
    }
  }

  const staleUnreportedEvents = await getStaleUnreportedEventCount(2);
  if (staleUnreportedEvents >= 25) {
    await sendSlackAlert(
      `[Aletheia PAYG] Usage reporting degraded: ${staleUnreportedEvents} usage events remain unreported for over 2 hours.`,
    );
  }

  return NextResponse.json({
    ok: true,
    candidates: users.length,
    reportedUsers,
    reportedUnits,
    failedUsers,
    staleUnreportedEvents,
  });
}
