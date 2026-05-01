import type { Metadata } from "next";
import SeoSolutionPage from "@/app/components/SeoSolutionPage";

export const metadata: Metadata = {
  title: "AI Runtime Security Layer | Aletheia Core",
  description:
    "Aletheia Core adds a runtime security layer between AI agents and tool execution, helping teams enforce policy before actions run.",
  alternates: { canonical: "https://aletheia-core.com/ai-runtime-security" },
  openGraph: {
    title: "AI Runtime Security Layer | Aletheia Core",
    description:
      "Aletheia Core adds a runtime security layer between AI agents and tool execution, helping teams enforce policy before actions run.",
    url: "https://aletheia-core.com/ai-runtime-security",
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

export default function AIRuntimeSecurityPage() {
  return (
    <SeoSolutionPage
      slug="/ai-runtime-security"
      title="Runtime Security for AI Systems"
      hero="Aletheia Core sits between your AI agent and the tools it wants to use. Before an action executes, the runtime checks whether the action is safe, policy-compliant, and auditable."
      problemPoints={[
        "Most AI safety focuses on model output, not action execution",
        "The real risk begins when an agent calls a tool, API, or backend system",
        "Prompt filters can be bypassed with encoding, indirection, or semantic disguise",
        "Without runtime enforcement, a filtered prompt can still trigger an unsafe action",
      ]}
      solveHeading="How Aletheia Core solves it"
      solveSteps={[
        "Agent proposes an action",
        "Aletheia Core inspects the action before any tool call",
        "Policy checks evaluate action and context",
        "System explicitly allows or blocks execution",
        "Signed receipt captures the final decision",
        "Flow: Agent → Proposed Action → Aletheia Core → Policy Check → Allow or Block → Signed Receipt",
      ]}
      useCases={[
        "AI app builders",
        "SaaS teams adding agent features",
        "Automation consultants",
        "Internal tool teams",
        "Security-conscious startups",
      ]}
      faq={faqItems}
      faqSchema={faqSchema}
    />
  );
}
