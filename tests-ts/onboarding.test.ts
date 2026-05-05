// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
/**
 * Onboarding gating tests.
 *
 * Verifies the four behaviors:
 *   1. Incomplete onboarding redirects to /onboarding from dashboard layout
 *   2. Completed onboarding allows dashboard access (no redirect)
 *   3. Partial onboarding state persists across calls (DB read, not in-memory)
 *   4. Completed user on /onboarding is redirected to /dashboard immediately
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

// --- Mocks ---

const mockUserProfileFindUnique = vi.fn();
const mockUserProfileUpsert = vi.fn();

vi.mock("@/lib/prisma", () => ({
  default: {
    userProfile: {
      findUnique: (...a: unknown[]) => mockUserProfileFindUnique(...a),
      upsert: (...a: unknown[]) => mockUserProfileUpsert(...a),
    },
  },
}));

// Capture redirect calls instead of throwing
const mockRedirect = vi.fn((path: string) => {
  throw Object.assign(new Error("NEXT_REDIRECT"), { digest: `NEXT_REDIRECT:${path}` });
});

vi.mock("next/navigation", () => ({
  redirect: (path: string) => mockRedirect(path),
}));

// --- Helpers ---

function captureRedirect(fn: () => Promise<unknown>): Promise<string | null> {
  return fn().then(() => null).catch((err: unknown) => {
    if (err instanceof Error && err.message === "NEXT_REDIRECT") {
      const digest = (err as { digest?: string }).digest ?? "";
      return digest.replace("NEXT_REDIRECT:", "");
    }
    throw err;
  });
}

async function loadOnboarding() {
  const mod = await import("@/lib/onboarding");
  return mod;
}

// --- Tests ---

describe("requireCompletedOnboarding", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
  });

  it("incomplete onboarding redirects to /onboarding from dashboard", async () => {
    // User exists but onboarding not complete
    mockUserProfileFindUnique.mockResolvedValue({
      userId: "user_incomplete",
      onboardingCompleted: false,
      useCase: "finance",   // partial state present
      primaryGoal: null,
    });

    const { requireCompletedOnboarding } = await loadOnboarding();
    const destination = await captureRedirect(() =>
      requireCompletedOnboarding("user_incomplete"),
    );

    expect(destination).toBe("/onboarding");
  });

  it("completed onboarding allows dashboard access — no redirect", async () => {
    mockUserProfileFindUnique.mockResolvedValue({
      userId: "user_complete",
      onboardingCompleted: true,
      useCase: "finance",
      primaryGoal: "risk_management",
    });

    const { requireCompletedOnboarding } = await loadOnboarding();

    // Must not throw / redirect
    const profile = await requireCompletedOnboarding("user_complete");
    expect(profile).toBeDefined();
    expect(profile?.onboardingCompleted).toBe(true);
    expect(mockRedirect).not.toHaveBeenCalled();
  });

  it("partial onboarding state persists across sessions (DB is source of truth)", async () => {
    // Simulate two sequential calls (two page loads / sessions)
    const partialProfile = {
      userId: "user_partial",
      onboardingCompleted: false,
      useCase: "legal",     // step 1 filled in
      primaryGoal: null,    // step 2 not yet done
      agentType: null,
    };
    mockUserProfileFindUnique
      .mockResolvedValueOnce(partialProfile)  // first session
      .mockResolvedValueOnce(partialProfile); // second session (resumed)

    const { requireCompletedOnboarding } = await loadOnboarding();

    // Both sessions redirect to /onboarding (not to dashboard)
    const dest1 = await captureRedirect(() =>
      requireCompletedOnboarding("user_partial"),
    );
    const dest2 = await captureRedirect(() =>
      requireCompletedOnboarding("user_partial"),
    );

    expect(dest1).toBe("/onboarding");
    expect(dest2).toBe("/onboarding");
    // The DB was consulted each time (state not cached in-memory)
    expect(mockUserProfileFindUnique).toHaveBeenCalledTimes(2);
  });

  it("completed user is not re-redirected to /onboarding from dashboard", async () => {
    // This is the regression test: once onboardingCompleted === true,
    // the user must never be forced back to /onboarding.
    mockUserProfileFindUnique.mockResolvedValue({
      userId: "user_done",
      onboardingCompleted: true,
    });

    const { requireCompletedOnboarding } = await loadOnboarding();
    const profile = await requireCompletedOnboarding("user_done");

    expect(mockRedirect).not.toHaveBeenCalledWith("/onboarding");
    expect(profile?.onboardingCompleted).toBe(true);
  });
});

describe("redirectIfOnboardingComplete", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
  });

  it("completed user on /onboarding page is redirected to /dashboard", async () => {
    mockUserProfileFindUnique.mockResolvedValue({
      userId: "user_done",
      onboardingCompleted: true,
    });

    const { redirectIfOnboardingComplete } = await loadOnboarding();
    const destination = await captureRedirect(() =>
      redirectIfOnboardingComplete("user_done"),
    );

    expect(destination).toBe("/dashboard");
  });

  it("incomplete user on /onboarding page is NOT redirected away", async () => {
    mockUserProfileFindUnique.mockResolvedValue({
      userId: "user_new",
      onboardingCompleted: false,
    });

    const { redirectIfOnboardingComplete } = await loadOnboarding();
    const profile = await redirectIfOnboardingComplete("user_new");

    expect(mockRedirect).not.toHaveBeenCalled();
    expect(profile?.onboardingCompleted).toBe(false);
  });
});
