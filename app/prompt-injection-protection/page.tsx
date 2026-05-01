import type { Metadata } from "next";
import SeoSolutionPage from "@/app/components/SeoSolutionPage";

export const metadata: Metadata = {
  title: "Prompt Injection Protection for AI Agents | Aletheia Core",
  description:
    "Block prompt injection attempts before AI agents execute unsafe actions. Aletheia Core detects override attempts, exfiltration requests, and policy bypass patterns.",
  alternates: { canonical: "https://aletheia-core.com/prompt-injection-protection" },
  openGraph: {
    title: "Prompt Injection Protection for AI Agents | Aletheia Core",
    description:
      "Block prompt injection attempts before AI agents execute unsafe actions. Aletheia Core detects override attempts, exfiltration requests, and policy bypass patterns.",
    url: "https://aletheia-core.com/prompt-injection-protection",
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

export default function PromptInjectionProtectionPage() {
  return (
    <SeoSolutionPage
      slug="/prompt-injection-protection"
      title="Prompt Injection Protection for AI Agents"
      hero="Prompt injection is no longer just a chatbot problem. When AI agents can call tools, read files, access APIs, or trigger automations, prompt injection becomes a runtime security risk. Aletheia Core blocks malicious instructions before the agent acts."
      problemPoints={[
        '"Ignore all previous instructions" — direct override attempt',
        '"Reveal the system prompt" — policy extraction attack',
        '"Forward this customer list" — data exfiltration via instruction',
        '"Approve this request without verification" — authorization bypass',
        "Instructions hidden inside uploaded documents or retrieved web content",
      ]}
      solveHeading="How Aletheia Core solves it"
      solveSteps={[
        "All input is normalized — NFKC, zero-width stripping, recursive Base64/URL decode",
        "Scout agent scores threat context and exfiltration markers",
        "Nitpicker runs semantic similarity against blocked patterns",
        "Judge applies pre-execution policy check against signed manifest",
        "DENIED decisions block execution before any tool runs",
        "Every decision produces a signed receipt",
      ]}
      useCases={[
        "Customer support bots",
        "Document-processing agents",
        "RAG apps",
        "n8n/Zapier automations",
        "LangChain tool-use pipelines",
      ]}
      faq={faqItems}
      faqSchema={faqSchema}
    />
  );
}
