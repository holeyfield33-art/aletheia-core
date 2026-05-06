import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/auth", () => ({ authOptions: {} }));
vi.mock("@/lib/server-auth", () => ({
  requireAuth: vi.fn().mockResolvedValue({ user: { id: "user-1", plan: "TRIAL" } }),
}));
vi.mock("@/lib/onboarding", () => ({
  getUserOnboardingProfile: vi.fn().mockResolvedValue(null),
}));
vi.mock("@/lib/usage-tracking", () => ({
  getCurrentMonthUsage: vi.fn().mockResolvedValue(0),
}));

const mockAuditLogCount = vi.fn();
const mockAuditLogGroupBy = vi.fn();
const mockApiKeyCount = vi.fn();
const mockApiKeyAggregate = vi.fn();

vi.mock("@/lib/prisma", () => ({
  default: {
    auditLog: {
      count: (...a: unknown[]) => mockAuditLogCount(...a),
      groupBy: (...a: unknown[]) => mockAuditLogGroupBy(...a),
    },
    apiKey: {
      count: (...a: unknown[]) => mockApiKeyCount(...a),
      aggregate: (...a: unknown[]) => mockApiKeyAggregate(...a),
    },
  },
}));

beforeEach(() => {
  vi.resetModules();
  mockAuditLogCount.mockReset();
  mockAuditLogGroupBy.mockReset();
  mockApiKeyCount.mockResolvedValue(2);
  mockApiKeyAggregate.mockResolvedValue({ _sum: { requestsUsed: 100, monthlyQuota: 1000 } });
});

// Helper: import and run the RSC default export
async function runDashboard() {
  const { default: DashboardIndex } = await import("@/app/dashboard/page");
  return DashboardIndex();
}

describe("dashboard-counters", () => {
  it("returns proceeded and denied counts grouped correctly", async () => {
    mockAuditLogCount.mockResolvedValue(5);
    mockAuditLogGroupBy.mockResolvedValue([
      { decision: "PROCEED", _count: { decision: 3 } },
      { decision: "DENIED", _count: { decision: 2 } },
    ]);
    const element = await runDashboard();
    // Extract props passed to DashboardOverview
    const props = (element as React.ReactElement<{ proceededCount: number; deniedCount: number }>).props;
    expect(props.proceededCount).toBe(3);
    expect(props.deniedCount).toBe(2);
  });

  it("treats SANDBOX_BLOCKED and RATE_LIMITED as denied", async () => {
    mockAuditLogCount.mockResolvedValue(10);
    mockAuditLogGroupBy.mockResolvedValue([
      { decision: "PROCEED", _count: { decision: 7 } },
      { decision: "SANDBOX_BLOCKED", _count: { decision: 2 } },
      { decision: "RATE_LIMITED", _count: { decision: 1 } },
    ]);
    const element = await runDashboard();
    const props = (element as React.ReactElement<{ proceededCount: number; deniedCount: number }>).props;
    expect(props.proceededCount).toBe(7);
    expect(props.deniedCount).toBe(3);
  });

  it("returns zero counts for new user", async () => {
    mockAuditLogCount.mockResolvedValue(0);
    mockAuditLogGroupBy.mockResolvedValue([]);
    const element = await runDashboard();
    const props = (element as React.ReactElement<{ proceededCount: number; deniedCount: number; logCount: number }>).props;
    expect(props.logCount).toBe(0);
    expect(props.proceededCount).toBe(0);
    expect(props.deniedCount).toBe(0);
  });
});
