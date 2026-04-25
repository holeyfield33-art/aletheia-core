import { describe, it, expect } from "vitest";
import crypto from "node:crypto";
import { verifyStripeSignature } from "@/app/api/webhooks/stripe/route";

const SECRET = "whsec_test_secret_value_for_unit_tests";

function signedHeader(timestamp: number, body: string, secret = SECRET): string {
  const sig = crypto
    .createHmac("sha256", secret)
    .update(`${timestamp}.${body}`, "utf8")
    .digest("hex");
  return `t=${timestamp},v1=${sig}`;
}

describe("verifyStripeSignature", () => {
  const body = JSON.stringify({ id: "evt_test", type: "ping" });

  it("accepts a valid current signature", () => {
    const t = Math.floor(Date.now() / 1000);
    expect(verifyStripeSignature(body, signedHeader(t, body), SECRET)).toBe(true);
  });

  it("rejects a tampered body", () => {
    const t = Math.floor(Date.now() / 1000);
    const header = signedHeader(t, body);
    expect(verifyStripeSignature(body + "x", header, SECRET)).toBe(false);
  });

  it("rejects a stale timestamp (replay)", () => {
    const t = Math.floor(Date.now() / 1000) - 600;
    expect(verifyStripeSignature(body, signedHeader(t, body), SECRET)).toBe(false);
  });

  it("rejects a header missing v1 component", () => {
    const t = Math.floor(Date.now() / 1000);
    expect(verifyStripeSignature(body, `t=${t}`, SECRET)).toBe(false);
  });

  it("rejects a header missing timestamp", () => {
    expect(verifyStripeSignature(body, "v1=deadbeef", SECRET)).toBe(false);
  });

  it("rejects a header with non-numeric timestamp", () => {
    expect(verifyStripeSignature(body, "t=NaN,v1=deadbeef", SECRET)).toBe(false);
  });

  it("rejects when signed with the wrong secret", () => {
    const t = Math.floor(Date.now() / 1000);
    const header = signedHeader(t, body, "whsec_different_secret_value_xx");
    expect(verifyStripeSignature(body, header, SECRET)).toBe(false);
  });
});
