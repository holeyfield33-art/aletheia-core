/**
 * Single source of truth for all public product facts.
 * App pages import directly from here.
 * docs/index.html has a matching manual sync comment at top of file.
 *
 * When updating version, test count, or hosted API status:
 * 1. Update this file
 * 2. Update the <!-- PUBLIC FACTS SYNC --> block in docs/index.html
 */

export const PRODUCT = {
  name: "Aletheia Core",
  tagline:
    "Professional-grade runtime audit and pre-execution block layer for AI agents.",
  description:
    "Cryptographically signed enforcement, semantic policy hardening, and tamper-evident audit receipts for agentic workflows.",
  version: "1.9.2",
  testCount: 1193,
  license: "MIT",
  copyrightHolder: "Aletheia Sovereign Systems",
  copyrightYear: "2026",
  founder: "Joseph Holeyfield",
} as const;

export const URLS = {
  contact: "mailto:info@aletheia-core.com?subject=Service Inquiry",
  contactEmail: "info@aletheia-core.com",
  github: "https://github.com/holeyfield33-art/aletheia-core",
  landingPage: "https://aletheia-core.com",
  appBase: "https://app.aletheia-core.com",
  demo: "https://app.aletheia-core.com/demo",
  verify: "https://app.aletheia-core.com/verify",
  pricing: "https://app.aletheia-core.com/#pricing",
} as const;

export const STATUS = {
  /**
   * "live" | "launching" | "private-beta" | "unavailable"
   * Only mark "live" when hosted API is publicly accessible.
   */
  hostedApi: "live" as const,
  hostedApiLabel: "Hosted API — live",
  servicesAvailable: true,
  openSource: true,
} as const;

export const SEO_SOLUTIONS = [
  {
    href: "/ai-agent-security",
    title: "AI Agent Security",
    summary: "Runtime protection for tool-using AI agents.",
  },
  {
    href: "/prompt-injection-protection",
    title: "Prompt Injection Protection",
    summary:
      "Block override attempts, unsafe instructions, and data exfiltration prompts.",
  },
  {
    href: "/ai-runtime-security",
    title: "AI Runtime Security",
    summary: "Enforce policy before agent actions execute.",
  },
  {
    href: "/signed-audit-receipts",
    title: "Signed Audit Receipts",
    summary: "Generate verifiable proof of agent decisions.",
  },
  {
    href: "/ai-agent-guardrails",
    title: "AI Agent Guardrails",
    summary: "Add pre-execution safety controls to autonomous systems.",
  },
] as const;

export const CTAS = {
  primary: { label: "Try Live Demo", href: "/demo" },
  services: {
    label: "Book Services",
    href: URLS.contact,
  },
  pricing: { label: "Pricing", href: "/#pricing" },
  github: { label: "View GitHub", href: URLS.github },
  docs: { label: "Read Docs", href: URLS.landingPage },
  trial: { label: "Start Free", href: "/dashboard/keys" },
  upgrade: { label: "Upgrade Hosted Plan", href: "/dashboard" },
} as const;

export const PRICING = {
  free: { receipts: 1000, price: 0 },
  scale: {
    receipts: 25000,
    price: 19,
    stripePriceId: process.env.STRIPE_SCALE_PRICE_ID,
  },
  pro: {
    receipts: 100000,
    price: 49,
    stripePriceId: process.env.STRIPE_PRO_PRICE_ID,
  },
  payg: {
    name: "Pay as You Go",
    pricePerReceipt: 0.00049,
    stripePriceId: process.env.STRIPE_PAYG_METERED_PRICE_ID,
    isMetered: true,
    description: "No monthly fee. Pay only for what you use.",
  },
} as const;
