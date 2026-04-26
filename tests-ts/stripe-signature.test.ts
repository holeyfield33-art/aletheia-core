import { describe, it, expect } from "vitest";
import crypto from "node:crypto";
import { verifyStripeSignature } from "@/app/api/webhooks/stripe/route";

const TEST_KEY = "whsec_test_key_value_for_unit_tests";

function signedHeader(timestamp: number, body: string, key = TEST_KEY): string {
  const sig = crypto
    .createHmac("sha256", key)
    .update(`${timestamp}.${body}`, "utf8")
    .digest("hex");
  return `t=${timestamp},v1=${sig}`;
}

describe("verifyStripeSignature", () => {
  const body = JSON.stringify({ id: "evt_test", type: "ping" });

  it("accepts a valid current signature", () => {
    const t = Math.floor(Date.now() / 1000);
    expect(verifyStripeSignature(body, signedHeader(t, body), TEST_KEY)).toBe(true);
  });

  it("rejects a tampered body", () => {
    const t = Math.floor(Date.now() / 1000);
    const header = signedHeader(t, body);
    expect(verifyStripeSignature(body + "x", header, TEST_KEY)).toBe(false);
  });

  it("rejects a stale timestamp (replay)", () => {
    const t = Math.floor(Date.now() / 1000) - 600;
    expect(verifyStripeSignature(body, signedHeader(t, body), TEST_KEY)).toBe(false);
  });

  it("rejects a header missing v1 component", () => {
    const t = Math.floor(Date.now() / 1000);
    expect(verifyStripeSignature(body, `t=${t}`, TEST_KEY)).toBe(false);
  });

  it("rejects a header missing timestamp", () => {
    expect(verifyStripeSignature(body, "v1=deadbeef", TEST_KEY)).toBe(false);
  });

  it("rejects a header with non-numeric timestamp", () => {
    expect(verifyStripeSignature(body, "t=NaN,v1=deadbeef", TEST_KEY)).toBe(false);
  });

  it("rejects when signed with the wrong key", () => {
    const t = Math.floor(Date.now() / 1000);
    const header = signedHeader(t, body, "whsec_different_key_value_xx");
    expect(verifyStripeSignature(body, header, TEST_KEY)).toBe(false);
  });
});
