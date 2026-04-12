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
  tagline: "Professional-grade runtime audit and pre-execution block layer for AI agents.",
  description:
    "Cryptographically signed enforcement, semantic policy hardening, and tamper-evident audit receipts for agentic workflows.",
  version: "1.6.2",
  testCount: 689,
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

export const CTAS = {
  primary: { label: "Try Live Demo", href: "/demo" },
  services: {
    label: "Book Services",
    href: URLS.contact,
  },
  pricing: { label: "Pricing", href: "/#pricing" },
  github: { label: "View GitHub", href: URLS.github },
  docs: { label: "Read Docs", href: URLS.landingPage },
  trial: { label: "Start Free Trial", href: "/dashboard/keys" },
  upgrade: { label: "Upgrade to Hosted Pro", href: "/api/stripe/checkout" },
} as const;
