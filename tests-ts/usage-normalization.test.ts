import { describe, expect, it } from "vitest";

import { normalizeKeyUsage } from "@/app/dashboard/usage/page";

describe("normalizeKeyUsage", () => {
  it("maps camelCase API fields through unchanged", () => {
    expect(
      normalizeKeyUsage({
        id: "key_1",
        name: "Primary",
        keyPrefix: "sk_trial_...abcd",
        plan: "TRIAL",
        status: "active",
        monthlyQuota: 1000,
        requestsUsed: 25,
        periodStart: "2026-05-01T00:00:00.000Z",
        periodEnd: "2026-06-01T00:00:00.000Z",
        createdAt: "2026-05-01T00:00:00.000Z",
        lastUsedAt: "2026-05-04T00:00:00.000Z",
      }),
    ).toMatchObject({
      keyPrefix: "sk_trial_...abcd",
      monthlyQuota: 1000,
      requestsUsed: 25,
      periodStart: "2026-05-01T00:00:00.000Z",
      lastUsedAt: "2026-05-04T00:00:00.000Z",
    });
  });

  it("accepts legacy snake_case payloads for compatibility", () => {
    expect(
      normalizeKeyUsage({
        id: "key_2",
        name: "Legacy",
        key_prefix: "sk_trial_...wxyz",
        plan: "TRIAL",
        status: "revoked",
        monthly_quota: 500,
        requests_used: 123,
        period_start: "2026-05-01T00:00:00.000Z",
        period_end: "2026-06-01T00:00:00.000Z",
        created_at: "2026-05-02T00:00:00.000Z",
        last_used_at: null,
      }),
    ).toMatchObject({
      keyPrefix: "sk_trial_...wxyz",
      monthlyQuota: 500,
      requestsUsed: 123,
      periodStart: "2026-05-01T00:00:00.000Z",
      lastUsedAt: null,
    });
  });
});
