// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems

import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

// --- Mocks ---

const mockFindFirst = vi.fn();

vi.mock("@/lib/prisma", () => ({
  default: {
    auditLog: {
      findFirst: (...args: unknown[]) => mockFindFirst(...args),
    },
  },
}));

vi.mock("@/lib/auth", () => ({
  authOptions: {},
}));

vi.mock("@/lib/api-utils", () => ({
  secureJson: (data: unknown, init?: ResponseInit) =>
    new Response(JSON.stringify(data), {
      status: init?.status ?? 200,
      headers: { "Content-Type": "application/json" },
    }),
}));

const mockGetServerSession = vi.fn();

vi.mock("next-auth", () => ({
  getServerSession: (...args: unknown[]) => mockGetServerSession(...args),
}));

// --- Helpers ---

function makeRequest(id: string): NextRequest {
  return new NextRequest(`http://localhost/api/logs/${id}`);
}

function makeParams(id: string) {
  return { params: { id } };
}

async function loadRoute() {
  const mod = await import("@/app/api/logs/[id]/route");
  return mod;
}

// --- Tests ---

describe("GET /api/logs/[id]", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
  });

  it("test_logs_id_returns_401_when_unauthenticated", async () => {
    mockGetServerSession.mockResolvedValue(null);
    const { GET } = await loadRoute();

    const req = makeRequest("log_abc");
    const res = await GET(req, makeParams("log_abc"));
    expect(res.status).toBe(401);

    const body = await res.json();
    expect(body.error).toBe("unauthorized");
  });

  it("test_logs_id_returns_full_row_with_receipt", async () => {
    mockGetServerSession.mockResolvedValue({ user: { id: "user_a" } });
    const fakeLog = {
      id: "log_abc",
      decision: "DENIED",
      action: "Transfer_Funds",
      origin: "agent-001",
      threatScore: 8.5,
      reason: "Semantic veto",
      latencyMs: 42,
      requestId: "req_xyz",
      receipt: { sig: "abc123", payload: "test" },
      createdAt: new Date().toISOString(),
    };
    mockFindFirst.mockResolvedValue(fakeLog);

    const { GET } = await loadRoute();

    const req = makeRequest("log_abc");
    const res = await GET(req, makeParams("log_abc"));
    expect(res.status).toBe(200);

    const body = await res.json();
    expect(body.log).toBeDefined();
    expect(body.log.receipt).toEqual(fakeLog.receipt);
    expect(body.log.latencyMs).toBe(42);

    // Confirm findFirst was called with user-scoped filter (IDOR prevention)
    const callArgs = mockFindFirst.mock.calls[0][0];
    expect(callArgs.where.id).toBe("log_abc");
    expect(callArgs.where.userId).toBe("user_a");
  });

  it("test_logs_id_returns_404_for_other_users_log", async () => {
    // Authenticated as user_b, but findFirst returns null (log belongs to user_a)
    mockGetServerSession.mockResolvedValue({ user: { id: "user_b" } });
    mockFindFirst.mockResolvedValue(null);

    const { GET } = await loadRoute();

    const req = makeRequest("log_abc");
    const res = await GET(req, makeParams("log_abc"));

    // Must return 404 — not 403, not 200. No existence leak.
    expect(res.status).toBe(404);

    const body = await res.json();
    expect(body.error).toBe("not_found");
  });
});
