// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems

import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

// --- Mocks ---

vi.mock("@/lib/auth", () => ({
  authOptions: {},
}));

vi.mock("@/lib/auth-config", () => ({
  getBaseUrl: () => "https://app.aletheia-core.com",
}));

vi.mock("stripe", () => ({
  default: vi.fn(),
}));

vi.mock("@/lib/prisma", () => ({
  default: {
    user: { findUnique: vi.fn() },
  },
}));

const mockGetServerSession = vi.fn();
vi.mock("next-auth", () => ({
  getServerSession: (...args: unknown[]) => mockGetServerSession(...args),
}));

// --- Helper ---

function makeSameOriginRequest(body: unknown, url = "https://app.aletheia-core.com/api/stripe/checkout"): NextRequest {
  return new NextRequest(url, {
    method: "POST",
    headers: {
      "sec-fetch-site": "same-origin",
      "content-type": "application/json",
    },
    body: JSON.stringify(body),
  });
}

async function loadRoute() {
  const mod = await import("@/app/api/stripe/checkout/route");
  return mod;
}

// --- Tests ---

describe("POST /api/stripe/checkout — enterprise tier", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    mockGetServerSession.mockResolvedValue({ user: { id: "user_a", email: "a@test.com" } });
  });

  it("test_stripe_checkout_enterprise_returns_mailto_url", async () => {
    const { POST } = await loadRoute();

    const req = makeSameOriginRequest({ tier: "enterprise" });
    const res = await POST(req);

    // Should be a JSON response (not a redirect) with a mailto: url
    expect(res.status).toBe(200);

    const body = await res.json();
    expect(typeof body.url).toBe("string");
    expect(body.url.startsWith("mailto:")).toBe(true);
    expect(body.url).toContain("aletheia-core.com");
    expect(body.url).toContain("Enterprise");
  });
});
