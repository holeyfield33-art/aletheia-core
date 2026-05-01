import { describe, it, expect } from "vitest";
import { authorizedCronRequest } from "@/app/api/cron/report-usage/route";

describe("authorizedCronRequest — constant-time cron auth", () => {
  const TEST_TOKEN = "test-cron-token-1234567890abcdef";

  it("rejects when secret is empty", () => {
    expect(authorizedCronRequest(`Bearer ${TEST_TOKEN}`, "")).toBe(false);
  });

  it("rejects when header is missing", () => {
    expect(authorizedCronRequest(null, TEST_TOKEN)).toBe(false);
  });

  it("rejects unrelated value", () => {
    expect(authorizedCronRequest("Bearer wrong", TEST_TOKEN)).toBe(false);
  });

  it("rejects when length differs (no panic from timingSafeEqual)", () => {
    expect(authorizedCronRequest(`Bearer ${TEST_TOKEN}x`, TEST_TOKEN)).toBe(
      false,
    );
    expect(
      authorizedCronRequest(`Bearer ${TEST_TOKEN.slice(0, -1)}`, TEST_TOKEN),
    ).toBe(false);
  });

  it("rejects same-prefix probes (defends against timing-attack reproduction)", () => {
    expect(
      authorizedCronRequest(
        "Bearer test-cron-token-aaaaaaaaaaaaaaaa",
        TEST_TOKEN,
      ),
    ).toBe(false);
  });

  it("accepts the exact value", () => {
    expect(authorizedCronRequest(`Bearer ${TEST_TOKEN}`, TEST_TOKEN)).toBe(
      true,
    );
  });
});
