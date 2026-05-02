import { redirect } from "next/navigation";
import prisma from "@/lib/prisma";

export const ONBOARDING_USE_CASE_OPTIONS = [
  "AI agent",
  "Chatbot",
  "MCP server",
  "Coding assistant",
  "Trading / finance workflow",
  "Internal automation",
  "Other",
] as const;

export const ONBOARDING_TOOL_OPTIONS = [
  "No tools yet",
  "Reads files",
  "Writes files",
  "Runs shell commands",
  "Calls APIs",
  "Uses MCP tools",
  "Handles payments or financial actions",
  "Not sure",
] as const;

export const ONBOARDING_RISK_OPTIONS = [
  "Prompt injection",
  "Secret leakage",
  "Unsafe shell execution",
  "MCP config tampering",
  "Unauthorized actions",
  "Compliance / audit trail",
  "I just want to test the demo",
] as const;

export type OnboardingRecommendation = {
  label: string;
  href: string;
};

export function serializeToolAccessProfile(values: string[]): string {
  return values.join(", ");
}

export function parseToolAccessProfile(value: string | null | undefined): string[] {
  if (!value) return [];
  return value
    .split(",")
    .map((entry) => entry.trim())
    .filter(Boolean);
}

export function getRecommendedAction(
  primaryGoal: string | null | undefined,
  useCase: string | null | undefined,
  agentType: string | null | undefined,
): OnboardingRecommendation {
  const normalizedGoal = primaryGoal ?? "";
  const normalizedUseCase = useCase ?? "";
  const normalizedAgentType = agentType ?? "";

  if (normalizedGoal === "I just want to test the demo") {
    return { label: "Run Live Demo", href: "/demo" };
  }
  if (normalizedGoal === "Compliance / audit trail") {
    return { label: "Verify Receipt", href: "/verify" };
  }
  if (
    [
      "Prompt injection",
      "Secret leakage",
      "Unsafe shell execution",
      "MCP config tampering",
    ].includes(normalizedGoal)
  ) {
    return { label: "Run Attack Scenario", href: "/demo" };
  }
  if (
    normalizedUseCase === "Trading / finance workflow" ||
    normalizedAgentType.includes("Handles payments or financial actions")
  ) {
    return { label: "Review Runtime Firewall", href: "/ai-agent-security" };
  }
  return { label: "Protect My Agent", href: "/auth/register?callbackUrl=%2Fdashboard" };
}

export async function getUserOnboardingProfile(userId: string) {
  return prisma.userProfile.findUnique({
    where: { userId },
  });
}

export async function requireCompletedOnboarding(userId: string) {
  const profile = await getUserOnboardingProfile(userId);
  if (!profile?.onboardingCompleted) {
    redirect("/onboarding");
  }
  return profile;
}

export async function redirectIfOnboardingComplete(userId: string) {
  const profile = await getUserOnboardingProfile(userId);
  if (profile?.onboardingCompleted) {
    redirect("/dashboard");
  }
  return profile;
}
