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
  tagline: "AI runtime security engine for agents and automations",
  description:
    "Block unsafe agent actions before execution. Every decision produces a signed audit receipt for independent verification.",
  version: "1.4.7",
  testCount: 296,
  license: "MIT",
  copyrightHolder: "Aletheia Sovereign Systems",
  copyrightYear: "2026",
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
  hostedApi: "launching" as const,
  hostedApiLabel: "Hosted API — launching",
  servicesAvailable: true,
  openSource: true,
} as const;

export const CTAS = {
  primary: { label: "Try Live Demo", href: "/demo" },
  services: {
    label: "Book a Service",
    href: URLS.contact,
  },
  pricing: { label: "View Pricing", href: "/#pricing" },
  github: { label: "GitHub", href: URLS.github },
} as const;
