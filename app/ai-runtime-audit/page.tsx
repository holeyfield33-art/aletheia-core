import type { Metadata } from "next";
import SeoLanding from "@/app/components/SeoLanding";
import { MARKETING_ORIGIN } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "AI Runtime Audit",
  description:
    "AI runtime audit blueprint for agent workflows: threat-model actions, enforce policy, and verify signed outcomes.",
  alternates: { canonical: `${MARKETING_ORIGIN}/ai-runtime-audit` },
};

export default function AIRuntimeAuditPage() {
  return (
    <SeoLanding
      slug="/ai-runtime-audit"
      eyebrow="SEO Landing"
      title="AI Runtime Audit for Production Agent Workflows"
      subtitle="Map your action surface, identify privilege escalation paths, and harden decision gates before deployment reaches scale."
      problemPoints={[
        "Agents can chain benign-looking operations into high-impact outcomes.",
        "Static controls miss context-dependent intent shifts during runtime.",
        "Teams struggle to prove why specific decisions were allowed or denied.",
      ]}
      flowSteps={[
        {
          name: "Surface Mapping",
          detail:
            "Catalog high-risk actions, data boundaries, and external systems touched by each agent pathway.",
        },
        {
          name: "Policy Binding",
          detail:
            "Attach enforceable policy checks to runtime decision points and verify signed manifest integrity.",
        },
        {
          name: "Receipt Validation",
          detail:
            "Record deterministic receipts per decision so compliance teams can verify execution intent after the fact.",
        },
      ]}
      useCases={[
        "Audit readiness for regulated AI operations",
        "Pre-launch risk review for autonomous workflows",
        "Internal control mapping across agent toolchains",
      ]}
      faq={[
        {
          q: "What does an AI runtime audit include?",
          a: "It covers action inventory, policy gate verification, attack simulation patterns, and receipt-level evidence quality.",
        },
        {
          q: "Can this run before production traffic?",
          a: "Yes. Teams can stage policy checks in evaluation mode and validate behavior before activating hard enforcement.",
        },
      ]}
      primaryCta={{ label: "Try Live Demo", href: "/demo" }}
      secondaryCta={{ label: "Read Docs", href: "/docs" }}
    />
  );
}
