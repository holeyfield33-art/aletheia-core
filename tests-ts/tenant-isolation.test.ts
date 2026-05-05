// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
/**
 * Multi-tenant isolation tests.
 *
 * For every tenant-scoped GET endpoint, this suite:
 *   1. Mocks session as User B
 *   2. Requests User A's data
 *   3. Asserts the response does NOT expose User A's data
 *   4. For ID-keyed routes: asserts 404 (not 403, not 200) -- no existence leak
 *
 * If any test here fails with the route returning 200 and User A's data,
 * that is a security bug -- stop and report immediately.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

// ------------------------------------------------------------------ mocks ---

const mockAuditLogFindMany = vi.fn();
const mockAuditLogFindFirst = vi.fn();
const mockAuditLogCount = vi.fn();
const mockApiKeyFindMany = vi.fn();
const mockApiKeyFindFirst = vi.fn();
const mockUserProfileFindUnique = vi.fn();

vi.mock("@/lib/prisma", () => ({
  default: {
    auditLog: {
      findMany: (...a: unknown[]) => mockAuditLogFindMany(...a),
      findFirst: (...a: unknown[]) => mockAuditLogFindFirst(...a),
      count: (...a: unknown[]) => mockAuditLogCount(...a),
    },
    apiKey: {
      findMany: (...a: unknown[]) => mockApiKeyFindMany(...a),
      findFirst: (...a: unknown[]) => mockApiKeyFindFirst(...a),
    },
    userProfile: {
      findUnique: (...a: unknown[]) => mockUserProfileFindUnique(...a),
    },
  },
}));

vi.mock("@/lib/auth", () => ({ authOptions: {} }));

vi.mock("@/lib/api-utils", () => ({
  secureJson: (data: unknown, init?: ResponseInit) =>
    new Response(JSON.stringify(data), {
      status: init?.status ?? 200,
      headers: { "Content-Type": "application/json" },
    }),
}));

const mockGetServerSession = vi.fn();
vi.mock("next-auth", () => ({
  getServerSession: (...a: unknown[]) => mockGetServerSession(...a),
}));

// --------------------------------------------------------- test fixtures ---

const USER_A_ID = "user_tenant_a";
const USER_B_ID = "user_tenant_b";

const USER_A_LOG = {
  id: "log_user_a_001",
  decision: "DENIED",
  action: "Transfer_Funds",
  origin: "agent-a",
  threatScore: 9.1,
  reason: "User A secret reason",
  latencyMs: 55,
  requestId: "req_user_a_001",
  receipt: { sig: "secret_sig_user_a" },
  createdAt: new Date().toISOString(),
};

const USER_A_KEY = {
  id: "key_user_a_001",
  userId: USER_A_ID,
  name: "User A production key",
  keyPrefix: "sk_a_...",
  plan: "PRO",
  status: "active",
  monthlyQuota: 5000,
  requestsUsed: 200,
};

const USER_A_PROFILE = {
  id: "profile_user_a",
  userId: USER_A_ID,
  fullName: "User A Full Name",
  email: "usera@example.com",
  onboardingCompleted: true,
};

// ------------------------------------------------------------ helpers ---

function makeGet(url: string): NextRequest {
  return new NextRequest(url);
}

// ================================================================ tests ===

describe("Tenant isolation — /api/logs", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    // Default: authenticated as User B
    mockGetServerSession.mockResolvedValue({ user: { id: USER_B_ID } });
  });

  it("list endpoint — User B sees empty list, not User A records", async () => {
    // Simulate DB returning nothing for User B (correct scoping)
    mockAuditLogFindMany.mockResolvedValue([]);
    mockAuditLogCount.mockResolvedValue(0);

    const { GET } = await import("@/app/api/logs/route");
    const res = await GET(makeGet("http://localhost/api/logs?page=1&limit=50"));
    expect(res.status).toBe(200);

    const body = await res.json();
    // Confirm the DB query was scoped to User B only
    const callArgs = mockAuditLogFindMany.mock.calls[0][0];
    expect(callArgs.where.userId).toBe(USER_B_ID);
    expect(callArgs.where.userId).not.toBe(USER_A_ID);

    // Confirm no User A data in response
    const logsJson = JSON.stringify(body);
    expect(logsJson).not.toContain("user_a");
    expect(logsJson).not.toContain("secret_sig_user_a");
  });

  it("detail endpoint — User B requesting User A log ID gets 404", async () => {
    // DB returns null because userId filter blocks User A's log
    mockAuditLogFindFirst.mockResolvedValue(null);

    const { GET } = await import("@/app/api/logs/[id]/route");
    const res = await GET(
      makeGet(`http://localhost/api/logs/${USER_A_LOG.id}`),
      { params: Promise.resolve({ id: USER_A_LOG.id }) },
    );

    expect(res.status).toBe(404);

    // Confirm the DB query included userId = User B (not User A)
    const callArgs = mockAuditLogFindFirst.mock.calls[0][0];
    expect(callArgs.where.id).toBe(USER_A_LOG.id);
    expect(callArgs.where.userId).toBe(USER_B_ID);

    const body = await res.json();
    expect(body.error).toBe("not_found");
    // Absolutely no User A data in the 404 response
    expect(JSON.stringify(body)).not.toContain("secret_sig_user_a");
  });
});

describe("Tenant isolation — /api/keys", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    mockGetServerSession.mockResolvedValue({ user: { id: USER_B_ID } });
  });

  it("list endpoint — query is scoped to User B", async () => {
    mockApiKeyFindMany.mockResolvedValue([]);

    const { GET } = await import("@/app/api/keys/route");
    const res = await GET();
    expect(res.status).toBe(200);

    const callArgs = mockApiKeyFindMany.mock.calls[0][0];
    expect(callArgs.where.userId).toBe(USER_B_ID);
    expect(callArgs.where.userId).not.toBe(USER_A_ID);

    const body = await res.json();
    expect(JSON.stringify(body)).not.toContain("User A production key");
  });
});

describe("Tenant isolation — /api/onboarding", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    mockGetServerSession.mockResolvedValue({
      user: { id: USER_B_ID, email: "userb@example.com" },
    });
  });

  it("GET onboarding — query is scoped to User B", async () => {
    mockUserProfileFindUnique.mockResolvedValue(null);

    const { GET } = await import("@/app/api/onboarding/route");
    const res = await GET();
    expect(res.status).toBe(200);

    const callArgs = mockUserProfileFindUnique.mock.calls[0][0];
    expect(callArgs.where.userId).toBe(USER_B_ID);
    expect(callArgs.where.userId).not.toBe(USER_A_ID);

    const body = await res.json();
    expect(JSON.stringify(body)).not.toContain("User A Full Name");
  });
});

describe("Tenant isolation — unauthenticated access", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    mockGetServerSession.mockResolvedValue(null);
  });

  it("/api/logs returns 401 to unauthenticated request", async () => {
    const { GET } = await import("@/app/api/logs/route");
    const res = await GET(makeGet("http://localhost/api/logs"));
    expect(res.status).toBe(401);
  });

  it("/api/logs/[id] returns 401 to unauthenticated request", async () => {
    const { GET } = await import("@/app/api/logs/[id]/route");
    const res = await GET(makeGet("http://localhost/api/logs/log_abc"), {
      params: Promise.resolve({ id: "log_abc" }),
    });
    expect(res.status).toBe(401);
  });

  it("/api/keys returns 401 to unauthenticated request", async () => {
    const { GET } = await import("@/app/api/keys/route");
    const res = await GET();
    expect(res.status).toBe(401);
  });
});
