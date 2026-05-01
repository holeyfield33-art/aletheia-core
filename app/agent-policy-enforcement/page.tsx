import type { Metadata } from "next";
import SeoLanding from "@/app/components/SeoLanding";
import { URLS } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "Agent Policy Enforcement",
  description:
    "Agent policy enforcement with signed manifests, semantic vetoes, and deterministic runtime denial controls.",
  alternates: { canonical: `${URLS.appBase}/agent-policy-enforcement` },
};

export default function AgentPolicyEnforcementPage() {
  return (
    <SeoLanding
      slug="/agent-policy-enforcement"
      eyebrow="Control Plane"
      title="Agent Policy Enforcement with Signed Runtime Controls"
      subtitle="Bind every high-risk action to policy primitives that are cryptographically verified before execution proceeds."
      problemPoints={[
        "Policy docs drift from actual runtime behavior across deployments.",
        "Alias phrases bypass exact action allow/deny lists.",
        "Teams need deterministic denial semantics for privileged operations.",
      ]}
      flowSteps={[
        {
          name: "Manifest Verification",
          detail:
            "Validate Ed25519 signatures and key metadata before loading policy to runtime memory.",
        },
        {
          name: "Action Gate",
          detail:
            "Check exact restricted actions and semantic aliases in a multi-step veto path.",
        },
        {
          name: "Deployment Drift Check",
          detail:
            "Reject mismatched policy bundles between workers to prevent partial rollout gaps.",
        },
      ]}
      useCases={[
        "Production policy enforcement for financial or admin actions",
        "Change-managed deployments that require signed policy provenance",
        "Fail-closed operations where uncertain context must deny",
      ]}
      faq={[
        {
          q: "Why use signed policy manifests?",
          a: "Signatures prevent silent policy tampering and prove enforcement inputs at runtime.",
        },
        {
          q: "Does it block only exact action names?",
          a: "No. It also evaluates semantic aliases and gray-zone intent cues to catch paraphrased restricted operations.",
        },
      ]}
      primaryCta={{ label: "Inspect Policy Controls", href: "/docs" }}
      secondaryCta={{ label: "Verify Receipt", href: "/verify" }}
    />
  );
}
