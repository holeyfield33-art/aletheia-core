import type { Metadata } from "next";
import SeoSolutionPage from "@/app/components/SeoSolutionPage";

export const metadata: Metadata = {
  title: "Signed Audit Receipts for AI Agents | Aletheia Core",
  description:
    "Generate signed audit receipts for AI agent actions, blocked requests, policy checks, and runtime enforcement decisions.",
  alternates: { canonical: "https://aletheia-core.com/signed-audit-receipts" },
  openGraph: {
    title: "Signed Audit Receipts for AI Agents | Aletheia Core",
    description:
      "Generate signed audit receipts for AI agent actions, blocked requests, policy checks, and runtime enforcement decisions.",
    url: "https://aletheia-core.com/signed-audit-receipts",
    type: "website",
  },
};

const faqSchema = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: [
    {
      "@type": "Question",
      name: "What is AI agent security?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "AI agent security protects systems where AI agents can call tools, access data, trigger workflows, or execute actions. It focuses on preventing unsafe behavior before the action happens.",
      },
    },
    {
      "@type": "Question",
      name: "What is runtime enforcement?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Runtime enforcement means checking an action while the system is running, before the agent executes it. This is different from reviewing logs after the fact.",
      },
    },
    {
      "@type": "Question",
      name: "What is prompt injection protection?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Prompt injection protection detects and blocks malicious instructions that try to override the agent's original rules, leak data, or force unsafe tool use.",
      },
    },
    {
      "@type": "Question",
      name: "What are signed audit receipts?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Signed audit receipts are cryptographic records of security decisions. They show what action was checked, what decision was made, and whether the receipt has been modified.",
      },
    },
  ],
};

const faqItems = [
  {
    q: "What is AI agent security?",
    a: "AI agent security protects systems where AI agents can call tools, access data, trigger workflows, or execute actions. It focuses on preventing unsafe behavior before the action happens.",
  },
  {
    q: "What is runtime enforcement?",
    a: "Runtime enforcement means checking an action while the system is running, before the agent executes it. This is different from reviewing logs after the fact.",
  },
  {
    q: "What is prompt injection protection?",
    a: "Prompt injection protection detects and blocks malicious instructions that try to override the agent's original rules, leak data, or force unsafe tool use.",
  },
  {
    q: "What are signed audit receipts?",
    a: "Signed audit receipts are cryptographic records of security decisions. They show what action was checked, what decision was made, and whether the receipt has been modified.",
  },
];

export default function SignedAuditReceiptsPage() {
  return (
    <SeoSolutionPage
      slug="/signed-audit-receipts"
      title="Signed Audit Receipts for AI Agent Actions"
      hero="AI agents need proof, not just logs. Aletheia Core generates signed audit receipts so teams can verify what an agent attempted, what policy was applied, and whether the action was allowed or blocked."
      problemPoints={[
        "Plain logs can be edited, deleted, or disputed",
        "No standard format exists for AI decision evidence",
        "Compliance teams need tamper-evident records, not screenshots",
        "Incident reviews need to prove what the agent saw and decided",
      ]}
      solveHeading="How Aletheia Core solves it"
      solveSteps={[
        "Request ID and timestamp",
        "Decision: PROCEED or DENIED",
        "Risk category and threat band",
        "Policy version and manifest signature status",
        "Payload fingerprint (SHA-256, not raw content)",
        "HMAC-SHA256 signature with 16-byte nonce",
      ]}
      useCases={[
        "AI agent compliance",
        "Security reviews",
        "Customer incident reports",
        "Internal governance",
        "Enterprise audit trails",
        "Red-team evidence",
      ]}
      faq={faqItems}
      faqSchema={faqSchema}
    />
  );
}
