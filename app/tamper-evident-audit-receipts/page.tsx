import type { Metadata } from "next";
import SeoLanding from "@/app/components/SeoLanding";
import { URLS } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "Tamper-Evident Audit Receipts",
  description:
    "Tamper-evident audit receipts for AI decisions using deterministic fields and cryptographic signature verification.",
  alternates: { canonical: `${URLS.appBase}/tamper-evident-audit-receipts` },
};

export default function TamperEvidentAuditReceiptsPage() {
  return (
    <SeoLanding
      slug="/tamper-evident-audit-receipts"
      eyebrow="Auditability"
      title="Tamper-Evident Audit Receipts for Every AI Decision"
      subtitle="Create machine-verifiable evidence that links decision outcomes to policy version, payload fingerprint, and origin context."
      problemPoints={[
        "Legacy logs are mutable and difficult to verify during incident review.",
        "Audit records often miss policy/version context needed for compliance.",
        "Cross-team investigations require deterministic evidence formats.",
      ]}
      flowSteps={[
        {
          name: "Canonical Record",
          detail:
            "Normalize decision metadata into a deterministic structure for reproducible signature checks.",
        },
        {
          name: "Signature Binding",
          detail:
            "Sign new records with Ed25519 receipt keys and scoped nonce values, while preserving verification for legacy HMAC receipts.",
        },
        {
          name: "Receipt Verification",
          detail:
            "Validate signatures and key fields to detect tampering or replay attempts in downstream workflows.",
        },
      ]}
      useCases={[
        "Compliance evidence exports for security reviews",
        "Internal forensics for denied vs allowed action disputes",
        "Automated attestations in high-risk release workflows",
      ]}
      faq={[
        {
          q: "What fields are included in a receipt?",
          a: "Decision, policy hash, payload fingerprint, action, origin, issued timestamp, nonce, and signature metadata.",
        },
        {
          q: "Can receipts be verified by another service?",
          a: "Yes. Verification can run independently as long as the service has the expected signature key and canonical field contract.",
        },
      ]}
      primaryCta={{ label: "Open Receipt Viewer", href: "/verify" }}
      secondaryCta={{ label: "Run Audit Demo", href: "/demo" }}
    />
  );
}
