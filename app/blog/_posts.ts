export type BlogPost = {
  slug: string;
  title: string;
  description: string;
  publishedAt: string;
  tags: string[];
  sections: Array<{ heading: string; body: string[] }>;
};

export const BLOG_POSTS: BlogPost[] = [
  {
    slug: "signed-policy-manifests-in-practice",
    title: "Signed Policy Manifests In Practice",
    description:
      "How Aletheia Core uses Ed25519 signatures to enforce policy integrity and fail closed when configuration drifts.",
    publishedAt: "2026-04-13",
    tags: ["security", "policy", "ed25519"],
    sections: [
      {
        heading: "Why Manifest Signing Matters",
        body: [
          "Unsigned policy files are mutable control planes. If an attacker can alter policy, they can silently downgrade enforcement.",
          "Aletheia Core treats policy as signed configuration, not trusted local state. That keeps runtime behavior pinned to approved intent.",
        ],
      },
      {
        heading: "The Verification Path",
        body: [
          "At startup, the backend verifies a detached Ed25519 signature for manifest/security_policy.json before loading restrictions.",
          "If verification fails, startup is denied for privileged flows. This protects against drift, tampering, and stale deployment artifacts.",
        ],
      },
      {
        heading: "Operational Pattern",
        body: [
          "Update the manifest in version control, sign it in CI or release workflow, and pin expected hashes per environment.",
          "This gives reproducible policy promotion while preserving a hard fail-closed posture in production.",
        ],
      },
    ],
  },
  {
    slug: "defense-in-depth-for-agentic-apis",
    title: "Defense In Depth For Agentic APIs",
    description:
      "A practical layering model for pre-execution controls, semantic vetoes, and tamper-evident receipts.",
    publishedAt: "2026-04-13",
    tags: ["agents", "api-security", "audit"],
    sections: [
      {
        heading: "Layer 1: Input Hardening",
        body: [
          "Normalize and decode user-controlled payloads before any semantic decisioning. This reduces obfuscation wins.",
          "NFKC normalization, control character stripping, and bounded decode depth are strong baseline controls.",
        ],
      },
      {
        heading: "Layer 2: Independent Gates",
        body: [
          "Aletheia separates Scout, Nitpicker, and Judge concerns. Any one layer can deny execution.",
          "Separating detection from enforcement limits single-point bypasses and improves explainability.",
        ],
      },
      {
        heading: "Layer 3: Receipts And Replay Defense",
        body: [
          "Decisions should emit signed receipts bound to policy version, manifest hash, and request identity.",
          "Replay-resistant tokens and hash-chained audit records create stronger forensic guarantees under incident pressure.",
        ],
      },
    ],
  },
  {
    slug: "shipping-secure-defaults-with-nextjs-and-fastapi",
    title: "Shipping Secure Defaults With Next.js And FastAPI",
    description:
      "Security defaults that reduce accidental exposure across frontend and API boundaries.",
    publishedAt: "2026-04-13",
    tags: ["nextjs", "fastapi", "hardening"],
    sections: [
      {
        heading: "Frontend Defaults",
        body: [
          "Keep API credentials server-side and proxy only what the client needs. Avoid leaking internal host details in errors.",
          "Maintain explicit CSP and route-aware robots/sitemap metadata so crawl behavior aligns with product intent.",
        ],
      },
      {
        heading: "Backend Defaults",
        body: [
          "Health endpoints should expose minimal public data and reserve diagnostics for authenticated callers.",
          "Regex and parser logic must be bounded to avoid algorithmic complexity attacks in high-throughput paths.",
        ],
      },
      {
        heading: "Release Hygiene",
        body: [
          "Pair build checks with integration tests that validate both security posture and customer-visible UX.",
          "Treat changelogs and docs as part of the release artifact so operators can reason about behavior changes quickly.",
        ],
      },
    ],
  },
];

export function getPostBySlug(slug: string): BlogPost | undefined {
  return BLOG_POSTS.find((post) => post.slug === slug);
}
