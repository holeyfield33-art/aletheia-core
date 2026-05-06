import { describe, it, expect, vi } from "vitest";

vi.mock("@/lib/public-keys", () => ({
  getReceiptPublicKey: vi.fn().mockResolvedValue({
    pem: "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEAGI282bHDtzH3fF2s8YjFM1px7zxiLKy1NRZirthzrH8=\n-----END PUBLIC KEY-----",
    keyId: "abc123",
  }),
  PublicKeyError: class PublicKeyError extends Error {
    status: number;
    code: string;
    constructor(status: number, code: string, message: string) {
      super(message);
      this.status = status;
      this.code = code;
    }
  },
}));

describe(".well-known/aletheia-receipt-key.pem route", () => {
  it("returns 200 with valid PEM content when key is configured", async () => {
    const { GET } = await import(
      "@/app/.well-known/aletheia-receipt-key.pem/route"
    );
    const response = await GET();
    expect(response.status).toBe(200);
    const text = await response.text();
    expect(text).toMatch(/^-----BEGIN PUBLIC KEY-----/);
    expect(text).toMatch(/-----END PUBLIC KEY-----/);
  });

  it("returns correct Content-Type header", async () => {
    const { GET } = await import(
      "@/app/.well-known/aletheia-receipt-key.pem/route"
    );
    const response = await GET();
    expect(response.headers.get("Content-Type")).toBe("application/x-pem-file");
  });
});
