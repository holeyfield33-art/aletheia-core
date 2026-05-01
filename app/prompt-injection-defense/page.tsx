import type { Metadata } from "next";
import SeoLanding from "@/app/components/SeoLanding";
import { URLS } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "Prompt Injection Defense",
  description:
    "Prompt injection defense for AI agents using layered normalization, semantic analysis, and fail-closed enforcement.",
  alternates: { canonical: `${URLS.appBase}/prompt-injection-defense` },
};

export default function PromptInjectionDefensePage() {
  return (
    <SeoLanding
      slug="/prompt-injection-defense"
      eyebrow="Security Design"
      title="Prompt Injection Defense for Autonomous Agents"
      subtitle="Detect instruction smuggling patterns early and block malicious intent before downstream systems are touched."
      problemPoints={[
        "System override prompts hide in long benign-looking narratives.",
        "Unicode confusables and encoding layers evade simplistic filters.",
        "Single-layer regex checks fail under paraphrased malicious intent.",
      ]}
      flowSteps={[
        {
          name: "Input Hardening",
          detail:
            "Apply NFKC normalization, confusable collapse, and bounded recursive decode to reveal hidden payload intent.",
        },
        {
          name: "Semantic Analysis",
          detail:
            "Score payload similarity against blocked intent patterns with static and vector-assisted checks.",
        },
        {
          name: "Fail-Closed Response",
          detail:
            "Deny risky actions and return sanitized reason classes without leaking internal thresholds.",
        },
      ]}
      useCases={[
        "Agent copilots exposed to untrusted user input",
        "Automation pipelines that execute tool or API actions",
        "Enterprise assistants with sensitive data access",
      ]}
      faq={[
        {
          q: "How is this different from prompt filtering?",
          a: "It combines normalization, semantic intent checks, and action-level veto controls instead of relying on keyword filtering alone.",
        },
        {
          q: "Can this handle encoded attacks?",
          a: "Yes. The hardening layer decodes bounded URL/Base64 chains and strips obfuscation artifacts before policy checks.",
        },
      ]}
      primaryCta={{ label: "Run Injection Scenario", href: "/demo" }}
      secondaryCta={{ label: "View Runtime Pipeline", href: "/#services" }}
    />
  );
}
