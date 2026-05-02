import type { Metadata } from "next";
import { requireAuth } from "@/lib/server-auth";
import {
  ONBOARDING_RISK_OPTIONS,
  ONBOARDING_TOOL_OPTIONS,
  ONBOARDING_USE_CASE_OPTIONS,
  redirectIfOnboardingComplete,
} from "@/lib/onboarding";
import OnboardingWizard from "@/app/components/onboarding/OnboardingWizard";

export const metadata: Metadata = {
  title: "Onboarding",
  description: "Set up your Aletheia Core runtime firewall path.",
};

export default async function OnboardingPage() {
  const session = await requireAuth();
  const profile = await redirectIfOnboardingComplete(session.user.id);

  return (
    <OnboardingWizard
      useCaseOptions={ONBOARDING_USE_CASE_OPTIONS}
      toolOptions={ONBOARDING_TOOL_OPTIONS}
      riskOptions={ONBOARDING_RISK_OPTIONS}
      initialProfile={profile}
      initialFullName={session.user.name}
    />
  );
}
