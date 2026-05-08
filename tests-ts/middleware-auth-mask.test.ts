import { describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import middleware from "@/middleware";

const getTokenMock = vi.fn();

vi.mock("next-auth/jwt", () => ({
  getToken: (...args: unknown[]) => getTokenMock(...args),
}));

describe("middleware anonymous API masking", () => {
  it("returns 404 not_found for unauthenticated protected API routes", async () => {
    getTokenMock.mockResolvedValueOnce(null);

    const request = new NextRequest("https://app.aletheia-core.com/api/keys");
    const response = await middleware(request);

    expect(response.status).toBe(404);
    await expect(response.json()).resolves.toEqual({ error: "not_found" });
  });

  it("keeps authenticated requests flowing for protected API routes", async () => {
    getTokenMock.mockResolvedValueOnce({ id: "user-1" });

    const request = new NextRequest("https://app.aletheia-core.com/api/keys");
    const response = await middleware(request);

    expect(response.status).toBe(200);
  });

  it("returns deterministic 404 for unsupported sensitive decoy pages", async () => {
    const request = new NextRequest("https://app.aletheia-core.com/account");
    const response = await middleware(request);

    expect(response.status).toBe(404);
    await expect(response.json()).resolves.toEqual({ error: "not_found" });
  });

  it("returns deterministic 404 for nested unsupported sensitive decoy pages", async () => {
    const request = new NextRequest("https://aletheia-core.com/admin/panel");
    const response = await middleware(request);

    expect(response.status).toBe(404);
    await expect(response.json()).resolves.toEqual({ error: "not_found" });
  });
});
