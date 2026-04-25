import { describe, it, expect } from "vitest";
import { authorizedCronRequest } from "@/app/api/cron/report-usage/route";

describe("authorizedCronRequest — constant-time cron auth", () => {
  const SECRET = "test-cron-secret-1234567890abcdef";

  it("rejects when secret is empty", () => {
    expect(authorizedCronRequest(`Bearer ${SECRET}`, "")).toBe(false);
  });

  it("rejects when header is missing", () => {
    expect(authorizedCronRequest(null, SECRET)).toBe(false);
  });

  it("rejects unrelated value", () => {
    expect(authorizedCronRequest("Bearer wrong", SECRET)).toBe(false);
  });

  it("rejects when length differs (no panic from timingSafeEqual)", () => {
    expect(authorizedCronRequest(`Bearer ${SECRET}x`, SECRET)).toBe(false);
    expect(authorizedCronRequest(`Bearer ${SECRET.slice(0, -1)}`, SECRET)).toBe(false);
  });

  it("rejects same-prefix probes (defends against timing-attack reproduction)", () => {
    expect(authorizedCronRequest("Bearer test-cron-secret-aaaaaaaaaaaaaaaa", SECRET)).toBe(false);
  });

  it("accepts the exact value", () => {
    expect(authorizedCronRequest(`Bearer ${SECRET}`, SECRET)).toBe(true);
  });
});
