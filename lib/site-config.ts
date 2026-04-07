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
  tagline: "Aletheia blocks malicious code before it installs.",
  description:
    "Detect supply-chain attacks in Python packages, dependencies, and runtime hooks — before execution.",
  version: "1.5.2",
  testCount: 527,
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
    label: "Book a Service",
    href: URLS.contact,
  },
  pricing: { label: "View Pricing", href: "/#pricing" },
  github: { label: "GitHub", href: URLS.github },
} as const;
