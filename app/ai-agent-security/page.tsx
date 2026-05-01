import type { Metadata } from "next";
import SeoSolutionPage from "@/app/components/SeoSolutionPage";

export const metadata: Metadata = {
  title: "AI Agent Security Runtime | Aletheia Core",
  description:
    "Aletheia Core is an open-source AI agent security runtime that checks agent actions before execution, blocks unsafe behavior, and generates signed audit receipts.",
  alternates: { canonical: "https://aletheia-core.com/ai-agent-security" },
  openGraph: {
    title: "AI Agent Security Runtime | Aletheia Core",
    description:
      "Aletheia Core is an open-source AI agent security runtime that checks agent actions before execution, blocks unsafe behavior, and generates signed audit receipts.",
    url: "https://aletheia-core.com/ai-agent-security",
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

export default function AIAgentSecurityPage() {
  return (
    <SeoSolutionPage
      slug="/ai-agent-security"
      title="AI Agent Security for Runtime Enforcement"
      hero="Aletheia Core protects AI agents before they execute unsafe actions. Instead of only scanning prompts, Aletheia Core checks proposed agent actions against signed policy manifests, semantic risk patterns, and cryptographic audit trails."
      problemPoints={[
        "AI agents call tools, access files, trigger workflows, and modify systems",
        "Security must happen before execution, not after damage is done",
        "Most safety layers only scan the prompt, not the planned action",
        "Logs after the fact cannot prevent harm that already occurred",
      ]}
      solveHeading="How Aletheia Core solves it"
      solveSteps={[
        "Agent proposes an action",
        "Aletheia Core normalizes and inspects the request",
        "Request is checked against a signed policy manifest",
        "Unsafe actions are blocked before execution",
        "A signed audit receipt is generated",
      ]}
      useCases={[
        "AI SaaS apps",
        "Internal copilots",
        "RAG pipelines",
        "Autonomous workflow agents",
        "Agentic customer support",
      ]}
      faq={faqItems}
      faqSchema={faqSchema}
    />
  );
}
