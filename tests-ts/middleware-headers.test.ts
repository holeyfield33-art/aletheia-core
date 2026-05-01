import { describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import middleware from "@/middleware";

vi.mock("next-auth/jwt", () => ({
  getToken: vi.fn().mockResolvedValue({ id: "user-1" }),
}));

describe("middleware security headers", () => {
  it("sets COOP, CORP, Permissions-Policy, and HSTS preload", async () => {
    const request = new NextRequest("https://app.aletheia-core.com/");
    const response = await middleware(request);

    expect(response.headers.get("Cross-Origin-Opener-Policy")).toBe(
      "same-origin",
    );
    expect(response.headers.get("Cross-Origin-Resource-Policy")).toBe(
      "same-origin",
    );
    expect(response.headers.get("Permissions-Policy")).toBe(
      "camera=(), microphone=(), geolocation=()",
    );
    expect(response.headers.get("Strict-Transport-Security")).toContain(
      "preload",
    );
  });

  it("emits nonce-based CSP without unsafe-inline script policy", async () => {
    const request = new NextRequest("https://app.aletheia-core.com/");
    const response = await middleware(request);

    const csp = response.headers.get("Content-Security-Policy") || "";

    expect(csp).toContain("script-src 'self' 'nonce-");
    expect(csp).toContain("'strict-dynamic'");
    expect(csp).not.toContain("script-src 'self' 'unsafe-inline'");
  });
});
