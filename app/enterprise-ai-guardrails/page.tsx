import type { Metadata } from "next";
import SeoLanding from "@/app/components/SeoLanding";
import { URLS } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "Enterprise AI Guardrails",
  description:
    "Enterprise AI guardrails for policy governance, staged enforcement, and operational resilience across agent systems.",
  alternates: { canonical: `${URLS.appBase}/enterprise-ai-guardrails` },
};

export default function EnterpriseAIGuardrailsPage() {
  return (
    <SeoLanding
      slug="/enterprise-ai-guardrails"
      eyebrow="Enterprise"
      title="Enterprise AI Guardrails for Policy-Driven Operations"
      subtitle="Deploy runtime guardrails that align engineering controls, compliance evidence, and operational response under one workflow."
      problemPoints={[
        "Enterprise teams need a clear path from policy to enforceable runtime decisions.",
        "High-risk actions require deterministic controls and reviewable evidence.",
        "Operational teams need staging controls before switching to full active mode.",
      ]}
      flowSteps={[
        {
          name: "Mode Governance",
          detail:
            "Stage controls in monitor/shadow modes, then transition to active deny enforcement under release gates.",
        },
        {
          name: "Risk Segmentation",
          detail:
            "Separate privileged from read-only pathways and apply strict denial rules during degraded states.",
        },
        {
          name: "Operational Readiness",
          detail:
            "Couple guardrails with smoke tests, incident playbooks, and rollback criteria for production reliability.",
        },
      ]}
      useCases={[
        "Enterprise rollouts with strict change-management requirements",
        "Cross-functional governance for AI reliability and security teams",
        "Regulated environments requiring clear audit and rollback controls",
      ]}
      faq={[
        {
          q: "Can teams enable guardrails gradually?",
          a: "Yes. You can roll out in staged modes and enforce hard deny paths only after validation milestones are met.",
        },
        {
          q: "How does this help incident response?",
          a: "Guardrails produce deterministic receipts and operational state checks that speed triage and rollback decisions.",
        },
      ]}
      primaryCta={{ label: "Read Operations Docs", href: "/docs" }}
      secondaryCta={{ label: "View Status", href: "/status" }}
    />
  );
}
