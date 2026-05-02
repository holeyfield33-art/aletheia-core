import type { Metadata } from "next";
import SeoSolutionPage from "@/app/components/SeoSolutionPage";

export const metadata: Metadata = {
  title: "AI Agent Guardrails for Tool-Using Systems",
  description:
    "Aletheia Core provides runtime guardrails for AI agents that call tools, APIs, workflows, and backend systems.",
  alternates: { canonical: "https://aletheia-core.com/ai-agent-guardrails" },
  openGraph: {
    title: "AI Agent Guardrails for Tool-Using Systems | Aletheia Core",
    description:
      "Aletheia Core provides runtime guardrails for AI agents that call tools, APIs, workflows, and backend systems.",
    url: "https://aletheia-core.com/ai-agent-guardrails",
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

export default function AIAgentGuardrailsPage() {
  return (
    <SeoSolutionPage
      slug="/ai-agent-guardrails"
      title="AI Agent Guardrails That Run Before Execution"
      hero="Guardrails should not only advise the model. They should protect the action boundary. Aletheia Core gives AI agents a pre-execution enforcement layer for risky actions, tool calls, and policy violations."
      problemPoints={[
        "Model-level guardrails can be bypassed through prompt manipulation",
        "Output filtering happens too late — the action may already be queued",
        "Guardrails built into the prompt are not enforced at the backend",
        "Autonomous agents need controls that survive adversarial inputs",
      ]}
      solveHeading="How Aletheia Core solves it"
      solveSteps={[
        "Pre-execution blocking — stops the action, not just the response",
        "Signed policy manifests — tamper-evident rules",
        "Cryptographic receipts — proof of every decision",
        "Semantic prompt-injection checks — catches disguised attacks",
        "Open-source core — fully auditable",
        "Hosted and enterprise options",
      ]}
      useCases={[
        "AI app builders",
        "SaaS teams adding agents",
        "Automation consultants",
        "Internal tool teams",
        "Security-conscious startups",
      ]}
      faq={faqItems}
      faqSchema={faqSchema}
    />
  );
}
