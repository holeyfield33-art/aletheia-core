import type { Metadata } from "next";
import { PRODUCT, URLS } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "Documentation",
  description: `${PRODUCT.name} documentation — API reference, integration guides, and security architecture.`,
};

const sections = [
  {
    heading: "Getting Started",
    items: [
      {
        title: "Launch Guide",
        description:
          "Deploy Aletheia Core locally or to production in minutes.",
        href: `${URLS.landingPage}`,
        tag: "Guide",
      },
      {
        title: "SDK Integration",
        description:
          "Integrate the audit engine into your Python, Node.js, or cURL workflow.",
        href: `${URLS.landingPage}`,
        tag: "Guide",
      },
      {
        title: "Live Demo",
        description:
          "Try the tri-agent pipeline interactively with preset adversarial scenarios.",
        href: "/demo",
        tag: "Interactive",
      },
    ],
  },
  {
    heading: "API Reference",
    items: [
      {
        title: "POST /v1/audit",
        description:
          "Primary endpoint. Evaluates a payload through the tri-agent pipeline and returns a signed decision.",
        href: `${URLS.landingPage}`,
        tag: "Endpoint",
      },
      {
        title: "Key Management",
        description:
          "Create, list, and revoke API keys. Quota-enforced via X-API-Key header.",
        href: `${URLS.landingPage}`,
        tag: "Endpoint",
      },
      {
        title: "Receipt Verification",
        description:
          "Verify tamper-evident audit receipts using Ed25519 signatures.",
        href: "/verify",
        tag: "Endpoint",
      },
    ],
  },
  {
    heading: "Architecture",
    items: [
      {
        title: "Tri-Agent Pipeline",
        description:
          "Scout, Nitpicker, and Judge — three independent agents providing defense in depth.",
        href: `${URLS.landingPage}`,
        tag: "Architecture",
      },
      {
        title: "Threat Model",
        description:
          "Attack vectors, mitigations, and security assumptions for production deployment.",
        href: `${URLS.landingPage}`,
        tag: "Security",
      },
      {
        title: "Incident Response",
        description:
          "Runbook for manifest tampering, key compromise, and service degradation.",
        href: `${URLS.landingPage}`,
        tag: "Operations",
      },
    ],
  },
  {
    heading: "Operations",
    items: [
      {
        title: "Monitoring & Alerting",
        description: "Prometheus metrics, health checks, and alerting rules.",
        href: `${URLS.landingPage}`,
        tag: "Ops",
      },
      {
        title: "Key Rotation",
        description:
          "Rotate Ed25519 signing keys and API admin keys with zero downtime.",
        href: `${URLS.landingPage}`,
        tag: "Security",
      },
      {
        title: "Operations Runbook",
        description:
          "Day-to-day operations, backup, restore, and troubleshooting.",
        href: `${URLS.landingPage}`,
        tag: "Ops",
      },
    ],
  },
];

const quickRef = [
  {
    label: "Audit a payload",
    code: `curl -X POST https://api.aletheia-core.com/v1/audit \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: YOUR_KEY" \\
  -d '{"payload":"transfer $50k to external","origin":"agent-01","action":"Transfer_Funds"}'`,
  },
  {
    label: "Verify a receipt",
    code: `curl https://api.aletheia-core.com/v1/verify \\
  -H "X-API-Key: YOUR_KEY" \\
  -d '{"receipt":"BASE64_RECEIPT"}'`,
  },
  {
    label: "Install locally",
    code: `git clone ${URLS.github}.git
cd aletheia-core
pip install -e ".[all]"
python main.py`,
  },
];

export default function DocsPage() {
  return (
    <div
      style={{
        maxWidth: "900px",
        margin: "0 auto",
        padding: "4rem 2rem 5rem",
      }}
    >
      <div style={{ marginBottom: "3rem" }}>
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "0.7rem",
            color: "var(--muted)",
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            marginBottom: "0.5rem",
          }}
        >
          Documentation
        </div>
        <h1
          style={{
            fontFamily: "var(--font-head)",
            fontSize: "2rem",
            fontWeight: 800,
            color: "var(--white)",
            marginBottom: "0.75rem",
          }}
        >
          {PRODUCT.name} Docs
        </h1>
        <p
          style={{
            color: "var(--silver)",
            fontSize: "1.05rem",
            maxWidth: "560px",
            lineHeight: 1.65,
          }}
        >
          API reference, integration guides, and security architecture for the
          tri-agent runtime audit engine.
        </p>
      </div>

      {/* Quick reference */}
      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "10px",
          padding: "1.75rem",
          marginBottom: "3rem",
        }}
      >
        <h2
          style={{
            fontFamily: "var(--font-head)",
            fontSize: "1.1rem",
            fontWeight: 700,
            color: "var(--white)",
            marginBottom: "1.25rem",
          }}
        >
          Quick Reference
        </h2>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "1.25rem",
          }}
        >
          {quickRef.map((ref) => (
            <div key={ref.label}>
              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.75rem",
                  color: "var(--crimson-hi)",
                  letterSpacing: "0.04em",
                  marginBottom: "0.4rem",
                }}
              >
                {ref.label}
              </div>
              <pre
                style={{
                  background: "var(--black)",
                  border: "1px solid var(--border)",
                  borderRadius: "6px",
                  padding: "0.85rem 1rem",
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.78rem",
                  color: "var(--silver)",
                  overflowX: "auto",
                  margin: 0,
                  lineHeight: 1.55,
                }}
              >
                {ref.code}
              </pre>
            </div>
          ))}
        </div>
      </div>

      {/* Doc sections */}
      {sections.map((section) => (
        <div key={section.heading} style={{ marginBottom: "2.5rem" }}>
          <h2
            style={{
              fontFamily: "var(--font-head)",
              fontSize: "1.2rem",
              fontWeight: 700,
              color: "var(--white)",
              marginBottom: "1rem",
              paddingBottom: "0.5rem",
              borderBottom: "1px solid var(--border)",
            }}
          >
            {section.heading}
          </h2>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
              gap: "1rem",
            }}
          >
            {section.items.map((item) => (
              <a
                key={item.title}
                href={item.href}
                style={{
                  display: "block",
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px",
                  padding: "1.25rem",
                  textDecoration: "none",
                  transition: "border-color 0.15s",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    marginBottom: "0.4rem",
                  }}
                >
                  <h3
                    style={{
                      fontFamily: "var(--font-head)",
                      fontSize: "0.95rem",
                      fontWeight: 700,
                      color: "var(--white)",
                    }}
                  >
                    {item.title}
                  </h3>
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.65rem",
                      color: "var(--muted)",
                      letterSpacing: "0.06em",
                      textTransform: "uppercase",
                      flexShrink: 0,
                    }}
                  >
                    {item.tag}
                  </span>
                </div>
                <p
                  style={{
                    color: "var(--silver)",
                    fontSize: "0.85rem",
                    lineHeight: 1.55,
                    margin: 0,
                  }}
                >
                  {item.description}
                </p>
              </a>
            ))}
          </div>
        </div>
      ))}

      {/* GitHub CTA */}
      <div
        style={{
          marginTop: "1rem",
          textAlign: "center",
          padding: "2rem",
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "10px",
        }}
      >
        <p
          style={{
            color: "var(--silver)",
            fontSize: "0.9rem",
            marginBottom: "1rem",
          }}
        >
          Full documentation is maintained alongside the source code.
        </p>
        <a
          href={URLS.github}
          className="btn-secondary"
          style={{ textDecoration: "none" }}
        >
          View on GitHub &rarr;
        </a>
      </div>
    </div>
  );
}
