import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/auth", () => ({ authOptions: {} }));

const mockGetServerSession = vi.fn();
vi.mock("next-auth", () => ({
  getServerSession: (...a: unknown[]) => mockGetServerSession(...a),
}));

// Dynamic import so mocks are set before module runs
async function renderCTA(props: Record<string, string | undefined> = {}) {
  // Re-import fresh each call (mocks already in place at module level)
  const { default: AuthAwareCTA } = await import(
    "@/app/components/AuthAwareCTA"
  );
  return AuthAwareCTA(props as Parameters<typeof AuthAwareCTA>[0]);
}

beforeEach(() => {
  vi.resetModules();
  mockGetServerSession.mockReset();
});

describe("AuthAwareCTA", () => {
  it("renders anonymous CTA when no session", async () => {
    mockGetServerSession.mockResolvedValue(null);
    const result = await renderCTA();
    // Anonymous path returns a React Fragment; first child is the primary anchor
    const fragment = result as React.ReactElement<{ children: React.ReactElement[] }>;
    const primaryAnchor = fragment.props.children[0] as React.ReactElement<{ href: string; children: string }>;
    expect(primaryAnchor.props.href).toBe("/auth/register");
    expect(primaryAnchor.props.children).toBe("Protect My Agent");
  });

  it("renders authed CTA when session exists", async () => {
    mockGetServerSession.mockResolvedValue({ user: { id: "user-1" } });
    const result = await renderCTA();
    const el = result as React.ReactElement<{ href: string; children: string }>;
    expect(el.props.href).toBe("/dashboard");
    expect(el.props.children).toBe("Open Dashboard");
  });

  it("renders both anonymous CTAs when secondary props provided", async () => {
    mockGetServerSession.mockResolvedValue(null);
    const result = await renderCTA({
      secondaryAnonymousLabel: "Sign In",
      secondaryAnonymousHref: "/auth/login",
    });
    // Fragment children: [primaryAnchor, secondaryAnchor]
    const fragment = result as React.ReactElement<{ children: React.ReactElement[] }>;
    const secondAnchor = fragment.props.children[1] as React.ReactElement<{ href: string }>;
    expect(secondAnchor.props.href).toBe("/auth/login");
  });

  it("only renders single authed CTA when secondary props provided to authed user", async () => {
    mockGetServerSession.mockResolvedValue({ user: { id: "user-1" } });
    const result = await renderCTA({
      secondaryAnonymousLabel: "Sign In",
      secondaryAnonymousHref: "/auth/login",
    });
    // Authed users get a single element, not a fragment with two children
    const el = result as React.ReactElement<{ href: string }>;
    expect(el.props.href).toBe("/dashboard");
  });
});
