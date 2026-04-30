import { beforeEach, describe, expect, it, vi } from "vitest";

const mockConsumeRateLimit = vi.fn();

vi.mock("@/lib/prisma", () => ({
  default: {
    loginAttempt: {
      count: vi.fn(),
      create: vi.fn(),
      deleteMany: vi.fn(),
    },
    user: {
      findUnique: vi.fn(),
    },
  },
}));

vi.mock("@/lib/rate-limit", () => ({
  consumeRateLimit: mockConsumeRateLimit,
}));

vi.mock("bcryptjs", () => ({
  default: {
    compare: vi.fn(),
  },
}));

async function loadAuthHelpers() {
  const setIntervalSpy = vi
    .spyOn(globalThis, "setInterval")
    .mockImplementation(() => 0 as unknown as NodeJS.Timeout);

  const authModule = await import("@/lib/auth");

  setIntervalSpy.mockRestore();
  return {
    extractClientIp: authModule.extractClientIp,
    consumeLoginIpRateLimit: authModule.consumeLoginIpRateLimit,
  };
}

describe("auth IP rate limiting", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();

    mockConsumeRateLimit.mockResolvedValue({
      allowed: true,
      retryAfterSeconds: 0,
      remaining: 19,
    });
  });

  it("uses the configured aggregate IP limit", async () => {
    const { consumeLoginIpRateLimit } = await loadAuthHelpers();

    mockConsumeRateLimit.mockResolvedValue({
      allowed: false,
      retryAfterSeconds: 60,
      remaining: 0,
    });

    const allowed = await consumeLoginIpRateLimit("203.0.113.10");

    expect(allowed).toBe(false);
    expect(mockConsumeRateLimit).toHaveBeenCalledWith(
      expect.objectContaining({
        action: "auth_login_ip",
        key: "203.0.113.10",
        limit: 20,
        windowMs: 15 * 60 * 1000,
      }),
    );
  });

  it("extracts client IP from x-forwarded-for before x-real-ip", async () => {
    const { extractClientIp } = await loadAuthHelpers();

    const ip = extractClientIp(
      new Headers({
        "x-forwarded-for": "198.51.100.8, 10.0.0.1",
        "x-real-ip": "198.51.100.24",
      }),
    );

    expect(ip).toBe("198.51.100.8");
  });

  it("falls back to x-real-ip when x-forwarded-for is missing", async () => {
    const { extractClientIp } = await loadAuthHelpers();

    const ip = extractClientIp(new Headers({ "x-real-ip": "198.51.100.24" }));

    expect(ip).toBe("198.51.100.24");
  });

  it("returns null when no IP headers are present", async () => {
    const { extractClientIp } = await loadAuthHelpers();

    expect(extractClientIp(new Headers())).toBeNull();
  });
});
