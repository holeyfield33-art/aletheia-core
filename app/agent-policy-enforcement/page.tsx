import type { Metadata } from "next";
import SeoLanding from "@/app/components/SeoLanding";
import { MARKETING_ORIGIN } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "Agent Policy Enforcement",
  description:
    "Agent policy enforcement with signed manifests, semantic vetoes, and deterministic runtime denial controls.",
  alternates: { canonical: `${MARKETING_ORIGIN}/agent-policy-enforcement` },
};

export default function AgentPolicyEnforcementPage() {
  return (
    <>
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
            q: "Can we tune block/proceed strictness?",
            a: "Yes. You can tighten or soften Scout, Nitpicker, Judge, and Qdrant category thresholds with environment variables and semantic manifest thresholds while keeping signature verification and restricted-action vetoes intact.",
          },
        ]}
        primaryCta={{ label: "Inspect Policy Controls", href: "/docs" }}
        secondaryCta={{ label: "Verify Receipt", href: "/verify" }}
      />

      <section style={{ padding: "0 2rem 5rem" }}>
        <div className="container" style={{ maxWidth: "980px" }}>
          <article
            style={{
              border: "1px solid var(--border)",
              borderRadius: "10px",
              background: "var(--surface)",
              padding: "1.35rem",
              marginBottom: "1rem",
            }}
          >
            <h2
              style={{
                fontFamily: "var(--font-head)",
                fontSize: "1.2rem",
                marginBottom: "0.75rem",
              }}
            >
              Signed Manifest Policy (Current Runtime)
            </h2>
            <p style={{ color: "var(--silver)", marginBottom: "0.8rem" }}>
              Current signed restricted actions include: Modify_Auth_Registry,
              Open_External_Socket, Bulk_Delete_Resource,
              Approve_Loan_Disbursement, Transfer_Funds, and Initiate_ACH.
            </p>
            <p style={{ color: "var(--muted)", fontSize: "0.9rem" }}>
              These action IDs are hard-vetoed by the Judge after signature
              verification and should only change through a manifest update and
              resign process.
            </p>
          </article>

          <article
            style={{
              border: "1px solid var(--border)",
              borderRadius: "10px",
              background: "var(--surface)",
              padding: "1.35rem",
            }}
          >
            <h2
              style={{
                fontFamily: "var(--font-head)",
                fontSize: "1.2rem",
                marginBottom: "0.75rem",
              }}
            >
              Tuning Controls (Soften or Tighten)
            </h2>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                gap: "0.8rem",
              }}
            >
              <div style={{ border: "1px solid var(--border-hi)", borderRadius: "8px", padding: "0.85rem" }}>
                <h3 style={{ marginBottom: "0.35rem", color: "var(--white)" }}>
                  Scout
                </h3>
                <p style={{ color: "var(--silver)", fontSize: "0.9rem" }}>
                  ALETHEIA_POLICY_THRESHOLD controls threat-score deny boundary.
                  Lower value = stricter block rate.
                </p>
              </div>
              <div style={{ border: "1px solid var(--border-hi)", borderRadius: "8px", padding: "0.85rem" }}>
                <h3 style={{ marginBottom: "0.35rem", color: "var(--white)" }}>
                  Nitpicker
                </h3>
                <p style={{ color: "var(--silver)", fontSize: "0.9rem" }}>
                  ALETHEIA_NITPICKER_SIMILARITY_THRESHOLD controls static
                  semantic block sensitivity. Lower value = stricter block rate.
                </p>
              </div>
              <div style={{ border: "1px solid var(--border-hi)", borderRadius: "8px", padding: "0.85rem" }}>
                <h3 style={{ marginBottom: "0.35rem", color: "var(--white)" }}>
                  Judge
                </h3>
                <p style={{ color: "var(--silver)", fontSize: "0.9rem" }}>
                  ALETHEIA_INTENT_THRESHOLD and ALETHEIA_GREY_ZONE_LOWER tune
                  semantic veto and grey-zone escalation.
                </p>
              </div>
              <div style={{ border: "1px solid var(--border-hi)", borderRadius: "8px", padding: "0.85rem" }}>
                <h3 style={{ marginBottom: "0.35rem", color: "var(--white)" }}>
                  Category Thresholds
                </h3>
                <p style={{ color: "var(--silver)", fontSize: "0.9rem" }}>
                  manifest semantic category thresholds let you tune by intent
                  class (auth, exfiltration, policy_evasion, etc.) instead of
                  using one global threshold.
                </p>
              </div>
            </div>
          </article>
        </div>
      </section>
    </>
  );
}
