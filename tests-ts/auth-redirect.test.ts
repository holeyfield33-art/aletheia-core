import { describe, it, expect } from "vitest";
import { resolveAuthRedirect } from "@/lib/auth";

const BASE = "https://app.aletheia-core.com";

describe("resolveAuthRedirect — open-redirect contract", () => {
  it("returns baseUrl for empty input", () => {
    expect(resolveAuthRedirect("", BASE)).toBe(BASE);
  });

  it("rejects protocol-relative redirects", () => {
    expect(resolveAuthRedirect("//evil.com/path", BASE)).toBe(BASE);
  });

  it("rejects backslash traversal in encoded relative paths", () => {
    expect(resolveAuthRedirect("/dashboard%5C..%5Cevil", BASE)).toBe(BASE);
  });

  it("rejects encoded protocol-relative redirects", () => {
    expect(resolveAuthRedirect("/%2Fevil.com", BASE)).toBe(BASE);
  });

  it("appends safe relative paths", () => {
    expect(resolveAuthRedirect("/dashboard", BASE)).toBe(`${BASE}/dashboard`);
  });

  it("rejects look-alike subdomain (origin-equality, not prefix)", () => {
    expect(
      resolveAuthRedirect("https://app.aletheia-core.com.evil/", BASE),
    ).toBe(BASE);
  });

  it("rejects userinfo-host smuggling", () => {
    expect(
      resolveAuthRedirect("https://app.aletheia-core.com@evil/", BASE),
    ).toBe(BASE);
  });

  it("accepts same-origin absolute URL", () => {
    const url = `${BASE}/dashboard?ok=1`;
    expect(resolveAuthRedirect(url, BASE)).toBe(url);
  });

  it("rejects unparseable URL", () => {
    expect(resolveAuthRedirect("ht!tp://", BASE)).toBe(BASE);
  });
});
