export type HostedPlanId = "TRIAL" | "PRO" | "MAX" | "ENTERPRISE";
export type ApiKeyPlanId = "trial" | "pro" | "max" | "enterprise";

export type HostedPlanConfig = {
  id: HostedPlanId;
  apiKeyPlan: ApiKeyPlanId;
  displayName: string;
  monthlyPriceCents: number;
  monthlyCalls: number;
  maxActiveKeys: number;
  logRetentionDays: number;
};

export const HOSTED_PLANS: Record<HostedPlanId, HostedPlanConfig> = {
  TRIAL: {
    id: "TRIAL",
    apiKeyPlan: "trial",
    displayName: "Hosted Trial",
    monthlyPriceCents: 0,
    monthlyCalls: 1_000,
    maxActiveKeys: 1,
    logRetentionDays: 7,
  },
  PRO: {
    id: "PRO",
    apiKeyPlan: "pro",
    displayName: "Hosted Scale",
    monthlyPriceCents: 1_900,
    monthlyCalls: 25_000,
    maxActiveKeys: 10,
    logRetentionDays: 30,
  },
  MAX: {
    id: "MAX",
    apiKeyPlan: "max",
    displayName: "Hosted Pro",
    monthlyPriceCents: 4_900,
    monthlyCalls: 100_000,
    maxActiveKeys: 10,
    logRetentionDays: 30,
  },
  ENTERPRISE: {
    id: "ENTERPRISE",
    apiKeyPlan: "enterprise",
    displayName: "Enterprise",
    monthlyPriceCents: 0,
    monthlyCalls: 2_147_483_647,
    maxActiveKeys: 10,
    logRetentionDays: 30,
  },
};

export function getHostedPlanConfig(plan: string | null | undefined): HostedPlanConfig {
  const normalized = typeof plan === "string" ? plan.toUpperCase() : "TRIAL";
  // Guard against prototype-walk lookups (e.g. plan="__proto__") — `??` would
  // not catch Object.prototype because it's truthy.
  if (!Object.hasOwn(HOSTED_PLANS, normalized)) return HOSTED_PLANS.TRIAL;
  return HOSTED_PLANS[normalized as HostedPlanId];
}

export function formatPlanPrice(cents: number): string {
  return cents === 0 ? "Free" : `$${(cents / 100).toFixed(2)}`;
}

export function getStripePriceIdForPlan(plan: HostedPlanId): string | undefined {
  if (plan === "PRO") return process.env.STRIPE_SCALE_PRICE_ID || process.env.STRIPE_PRO_PRICE_ID;
  if (plan === "MAX") return process.env.STRIPE_PRO_PRICE_ID;
  return undefined;
}

export function getStripeExpectedAmountForPlan(plan: HostedPlanId): number | undefined {
  if (plan === "PRO") {
    return parseInt(
      process.env.STRIPE_SCALE_PRICE_AMOUNT || String(HOSTED_PLANS.PRO.monthlyPriceCents),
      10,
    );
  }
  if (plan === "MAX") {
    return parseInt(process.env.STRIPE_PRO_PRICE_AMOUNT || String(HOSTED_PLANS.MAX.monthlyPriceCents), 10);
  }
  return undefined;
}

export function getStripeCurrencyForPlan(plan: HostedPlanId): string {
  if (plan === "PRO") {
    return (process.env.STRIPE_SCALE_CURRENCY || process.env.STRIPE_PRO_CURRENCY || "usd").toLowerCase();
  }
  return (process.env.STRIPE_PRO_CURRENCY || "usd").toLowerCase();
}
