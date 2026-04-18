import { PRODUCT, URLS, STATUS, CTAS } from "@/lib/site-config";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Aletheia Core — Runtime audit and pre-execution block layer for AI agents",
  description:
    "Cryptographically signed enforcement, semantic policy hardening, and tamper-evident audit receipts for agentic workflows.",
  alternates: { canonical: URLS.appBase },
};

export default function HomePage() {
  return (
    <>
      <Hero />
      <TrustBar />
      <hr style={{ border: "none", borderTop: "1px solid var(--border)" }} />
      <HowItWorks />
      <hr style={{ border: "none", borderTop: "1px solid var(--border)" }} />
      <BuiltInTheOpen />
      <hr style={{ border: "none", borderTop: "1px solid var(--border)" }} />
      <HowToUse />
      <hr style={{ border: "none", borderTop: "1px solid var(--border)" }} />
      <VerifyItYourself />
      <hr style={{ border: "none", borderTop: "1px solid var(--border)" }} />
      <RecentSecurityUpdates />
      <hr style={{ border: "none", borderTop: "1px solid var(--border)" }} />
      <Services />
    </>
  );
}

function Hero() {
  return (
    <section
      style={{
        maxWidth: "860px",
        margin: "0 auto",
        padding: "5.5rem 2rem 4rem",
        textAlign: "center",
      }}
    >
      <div
        style={{
          display: "inline-block",
          background: "var(--crimson-glow)",
          border: "1px solid var(--crimson)",
          color: "var(--silver)",
          fontFamily: "var(--font-mono)",
          fontSize: "0.77rem",
          padding: "0.3rem 0.8rem",
          borderRadius: "100px",
          marginBottom: "1.5rem",
          letterSpacing: "0.05em",
        }}
      >
        v{PRODUCT.version} &middot; {PRODUCT.license} License &middot;{" "}
        {PRODUCT.testCount} Tests Passing &middot; Hosted API {STATUS.hostedApi}
      </div>

      <h1
        style={{
          fontFamily: "var(--font-head)",
          fontSize: "clamp(2rem, 5vw, 3.2rem)",
          fontWeight: 800,
          lineHeight: 1.15,
          color: "var(--white)",
          marginBottom: "1.25rem",
        }}
      >
        Professional-grade{" "}
        <em style={{ color: "var(--crimson-hi)", fontStyle: "normal" }}>
          runtime audit
        </em>
        <br />
        and pre-execution block layer for AI agents.
      </h1>

      <p
        style={{
          fontSize: "1.05rem",
          color: "var(--silver)",
          maxWidth: "580px",
          margin: "0 auto 2.5rem",
          lineHeight: 1.7,
        }}
      >
        Cryptographically signed enforcement, semantic policy hardening, and
        tamper-evident audit receipts for agentic workflows.
      </p>

      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          gap: "0.75rem",
          alignItems: "center",
        }}
      >
        <a href="/demo" className="btn-primary">
          ▶ Try Live Demo
        </a>
        <a
          href={URLS.github}
          className="btn-secondary"
          target="_blank"
          rel="noopener noreferrer"
        >
          View GitHub
        </a>
      </div>
    </section>
  );
}

function TrustBar() {
  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "center",
        gap: "1.25rem",
        padding: "1rem 2rem 2rem",
      }}
    >
      {[
        `v${PRODUCT.version}`,
        "MIT Licensed",
        `${PRODUCT.testCount} Tests Passing`,
        "Signed Receipts",
        "Live Demo",
      ].map((item) => (
        <span
          key={item}
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "0.75rem",
            color: "var(--silver)",
            background: "var(--surface-2)",
            border: "1px solid var(--border-hi)",
            padding: "0.35rem 0.85rem",
            borderRadius: "100px",
            letterSpacing: "0.03em",
          }}
        >
          {item}
        </span>
      ))}
    </div>
  );
}

function HowItWorks() {
  const stages = [
    {
      num: "INPUT HARDENING",
      title: "Normalization",
      body: "NFKC homoglyph collapse, bidi/RTL override strip, recursive Base64/URL decode (up to 10 layers with budget cap), data-URI inline decode. All applied before any agent evaluates the payload.",
    },
    {
      num: "SEMANTIC SCORING",
      title: "Policy Evaluation",
      body: "Scout scores threat context. Nitpicker runs semantic similarity against blocked patterns. Cosine-similarity analysis against camouflage aliases.",
    },
    {
      num: "JUDGE (Ed25519)",
      title: "Decision",
      body: "Verifies the Ed25519 policy manifest. Applies pre-execution block against restricted actions. Produces a cryptographically bound decision.",
    },
    {
      num: "HMAC RECEIPT",
      title: "Receipt Signing",
      body: "Every decision — PROCEED or DENIED — produces an HMAC-SHA256 signed receipt with a unique 16-byte nonce, binding decision to policy hash, payload fingerprint, and origin.",
    },
  ];

  return (
    <section style={{ padding: "4rem 2rem" }}>
      <div className="container">
        <h2
          style={{
            fontFamily: "var(--font-head)",
            fontSize: "1.75rem",
            fontWeight: 800,
            color: "var(--white)",
            marginBottom: "0.5rem",
          }}
        >
          Verification Pipeline
        </h2>
        <p
          style={{
            color: "var(--silver)",
            marginBottom: "2.5rem",
            fontSize: "1rem",
          }}
        >
          Every request passes through a deterministic pipeline. Each stage must clear independently.
        </p>

        {/* Pipeline flow diagram */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "0",
            marginBottom: "2.5rem",
            overflowX: "auto",
            padding: "1.25rem 0",
          }}
        >
          {[
            { label: "Request", color: "var(--muted)" },
            { label: "Normalization", color: "var(--silver)" },
            { label: "Policy Evaluation", color: "var(--silver)" },
            { label: "Decision", color: "var(--crimson-hi)" },
            { label: "Receipt Signing", color: "var(--green)" },
            { label: "Audit Persistence", color: "var(--green)" },
          ].map((node, i, arr) => (
            <div key={node.label} style={{ display: "flex", alignItems: "center" }}>
              <div
                style={{
                  background: "var(--surface)",
                  border: `1px solid ${node.color}`,
                  padding: "0.5rem 1rem",
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.72rem",
                  color: node.color,
                  letterSpacing: "0.04em",
                  textTransform: "uppercase",
                  whiteSpace: "nowrap",
                }}
              >
                {node.label}
              </div>
              {i < arr.length - 1 && (
                <div
                  style={{
                    width: "24px",
                    height: "1px",
                    background: "var(--border-hi)",
                    position: "relative",
                  }}
                >
                  <div
                    style={{
                      position: "absolute",
                      right: "-3px",
                      top: "-3px",
                      width: 0,
                      height: 0,
                      borderTop: "3px solid transparent",
                      borderBottom: "3px solid transparent",
                      borderLeft: "5px solid var(--border-hi)",
                    }}
                  />
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Stage detail cards */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: "1.25rem",
          }}
        >
          {stages.map(({ num, title, body }) => (
            <div
              key={num}
              style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                padding: "1.5rem",
              }}
            >
              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.7rem",
                  color: "var(--crimson-hi)",
                  letterSpacing: "0.1em",
                  marginBottom: "0.5rem",
                  textTransform: "uppercase",
                }}
              >
                {num}
              </div>
              <h3
                style={{
                  fontFamily: "var(--font-head)",
                  fontSize: "1.05rem",
                  marginBottom: "0.5rem",
                  color: "var(--white)",
                }}
              >
                {title}
              </h3>
              <p style={{ fontSize: "0.88rem", color: "var(--silver)", lineHeight: 1.6 }}>
                {body}
              </p>
            </div>
          ))}
        </div>

        <ul
          style={{
            listStyle: "none",
            marginTop: "1.5rem",
            maxWidth: "620px",
            marginLeft: "auto",
            marginRight: "auto",
          }}
        >
          {[
            "Every decision is cryptographically signed — tamper-evident by design",
            "Fail-closed: invalid manifest or unverifiable action = automatic DENIED",
            "All three agents must pass independently — no single point of bypass",
            "Raw scores are never exposed to clients — only discretised threat bands",
          ].map((item) => (
            <li
              key={item}
              style={{
                display: "flex",
                gap: "0.6rem",
                padding: "0.5rem 0",
                fontSize: "0.88rem",
                color: "var(--silver)",
                lineHeight: 1.55,
              }}
            >
              <span style={{ color: "var(--green)", flexShrink: 0 }}>✓</span>
              {item}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function BuiltInTheOpen() {
  return (
    <section style={{ padding: "4rem 2rem", background: "var(--surface)" }}>
      <div className="container" style={{ maxWidth: "720px" }}>
        <h2
          style={{
            fontFamily: "var(--font-head)",
            fontSize: "1.75rem",
            fontWeight: 800,
            color: "var(--white)",
            marginBottom: "1rem",
          }}
        >
          Built in the open
        </h2>
        <p
          style={{
            color: "var(--silver)",
            fontSize: "1rem",
            lineHeight: 1.7,
            marginBottom: "1.25rem",
          }}
        >
          Aletheia Core is built by{" "}
          <strong style={{ color: "var(--white)" }}>{PRODUCT.founder}</strong>.
          The entire codebase is open source under the MIT License. Every
          detection rule, every policy check, and every decision path is
          auditable on GitHub. There are no black-box decisions — you can read
          every line that determines whether an action is allowed or blocked.
        </p>
        <p
          style={{
            color: "var(--silver)",
            fontSize: "0.95rem",
            lineHeight: 1.7,
            marginBottom: "1.5rem",
          }}
        >
          The security policy manifest is signed with Ed25519. Audit receipts
          are HMAC-SHA256 signed. If you don&apos;t trust the hosted API, run it
          yourself — the results are identical.
        </p>
        <div
          style={{
            background: "var(--surface-2)",
            border: "1px solid var(--border)",
            borderRadius: "8px",
            padding: "1rem 1.25rem",
            marginBottom: "1.5rem",
            fontFamily: "var(--font-mono)",
            fontSize: "0.82rem",
            color: "var(--silver)",
            lineHeight: 1.7,
          }}
        >
          <strong style={{ color: "var(--white)" }}>API Access:</strong>{" "}
          Use the live demo with no key, request a free trial key for evaluation,
          or upgrade to Hosted Pro for production API access and retained audit logs.
        </div>
        <a
          href={URLS.github}
          className="btn-secondary"
          target="_blank"
          rel="noopener noreferrer"
        >
          Browse the source on GitHub →
        </a>
      </div>
    </section>
  );
}

function HowToUse() {
  const options = [
    {
      label: "Community",
      name: "Self-hosted engine",
      price: "Free",
      priceDetail: "/ self-hosted",
      color: "var(--green)",
      description:
        "MIT-licensed open-source engine. Full control, self-hosted.",
      features: [
        "MIT licensed",
        "Self-hosted",
        "Core runtime protection",
        "Signed receipts",
        "Community support",
      ],
      cta: { label: "View on GitHub", href: URLS.github },
      ctaStyle: "secondary" as const,
    },
    {
      label: "Hosted Trial",
      name: "Free evaluation",
      price: "Free",
      priceDetail: "/ evaluation",
      color: "var(--silver)",
      description:
        "Free evaluation key with 1,000 requests/month. No credit card required.",
      features: [
        "Free evaluation key",
        "1,000 requests / month",
        "One API key",
        "Evaluation use only",
      ],
      cta: { label: "Start Free Trial", href: "/dashboard/keys" },
      ctaStyle: "secondary" as const,
    },
    {
      label: "Hosted Pro",
      name: "Production API",
      price: "$49",
      priceDetail: "/mo",
      color: "var(--crimson-hi)",
      description:
        "Production API access with 100,000 requests/month, retained audit logs, and priority support.",
      features: [
        "Production API access",
        "100,000 requests / month",
        "30-day audit logs",
        "Up to 10 API keys",
        "Priority support",
      ],
      cta: {
        label: "Upgrade to Hosted Pro",
        href: "/dashboard",
      },
      ctaStyle: "primary" as const,
      highlight: true,
    },
    {
      label: "Services",
      name: "Expert engagement",
      price: "From $2,500",
      priceDetail: "",
      color: "var(--silver)",
      description:
        "Agent red-team review, custom policy engineering, runtime security integration, and deployment guidance.",
      features: [
        "Agent red-team review",
        "Custom policy engineering",
        "Runtime security integration",
        "Deployment guidance",
      ],
      cta: {
        label: "Book Services",
        href: `mailto:${URLS.contactEmail}?subject=Service Inquiry`,
      },
      ctaStyle: "secondary" as const,
    },
  ];

  return (
    <section id="pricing" style={{ padding: "5rem 2rem" }}>
      <div className="container">
        <h2
          style={{
            fontFamily: "var(--font-head)",
            fontSize: "1.75rem",
            fontWeight: 800,
            color: "var(--white)",
            marginBottom: "0.5rem",
          }}
        >
          Pricing
        </h2>
        <p
          style={{
            color: "var(--silver)",
            marginBottom: "2.5rem",
            fontSize: "1rem",
          }}
        >
          Open-source core. Hosted API for evaluation and production. Expert services available.
        </p>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))",
            gap: "1.5rem",
          }}
        >
          {options.map((opt) => (
            <div
              key={opt.name}
              style={{
                background: opt.highlight
                  ? "var(--surface-2)"
                  : "var(--surface)",
                border: opt.highlight
                  ? "1px solid var(--crimson)"
                  : "1px solid var(--border)",
                borderRadius: "10px",
                padding: "1.75rem",
                display: "flex",
                flexDirection: "column",
                gap: "1rem",
              }}
            >
              <div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    marginBottom: "0.75rem",
                  }}
                >
                  <h3
                    style={{
                      fontFamily: "var(--font-head)",
                      fontSize: "1.15rem",
                      color: "var(--white)",
                    }}
                  >
                    {opt.name}
                  </h3>
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.72rem",
                      color: opt.color,
                      letterSpacing: "0.06em",
                    }}
                  >
                    {opt.label}
                  </span>
                </div>
                <div
                  style={{
                    marginBottom: "0.5rem",
                  }}
                >
                  <span
                    style={{
                      fontFamily: "var(--font-head)",
                      fontSize: "1.5rem",
                      fontWeight: 800,
                      color: "var(--white)",
                    }}
                  >
                    {opt.price}
                  </span>
                  {opt.priceDetail && (
                    <span
                      style={{
                        color: "var(--muted)",
                        fontSize: "0.82rem",
                        marginLeft: "0.3rem",
                      }}
                    >
                      {opt.priceDetail}
                    </span>
                  )}
                </div>
                <p
                  style={{
                    color: "var(--silver)",
                    fontSize: "0.88rem",
                    lineHeight: 1.55,
                  }}
                >
                  {opt.description}
                </p>
              </div>
              <ul style={{ listStyle: "none", flex: 1 }}>
                {opt.features.map((f) => (
                  <li
                    key={f}
                    style={{
                      display: "flex",
                      gap: "0.6rem",
                      padding: "0.4rem 0",
                      fontSize: "0.87rem",
                      color: "var(--silver)",
                      borderBottom: "1px solid var(--border)",
                    }}
                  >
                    <span style={{ color: "var(--green)", flexShrink: 0 }}>
                      ✓
                    </span>
                    {f}
                  </li>
                ))}
              </ul>
              <a
                href={opt.cta.href}
                className={
                  opt.ctaStyle === "primary" ? "btn-primary" : "btn-secondary"
                }
                style={{
                  justifyContent: "center",
                  textAlign: "center",
                  marginTop: "0.5rem",
                }}
                {...(opt.cta.href.startsWith("http")
                  ? { target: "_blank", rel: "noopener noreferrer" }
                  : {})}
              >
                {opt.cta.label}
              </a>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function RecentSecurityUpdates() {
  const updates = [
    {
      title: "Enterprise Auth & RBAC",
      body: "OIDC, SAML, and API-key authentication with role-based access control (admin/operator/viewer). Per-tenant key store with quota enforcement.",
      isNew: true,
    },
    {
      title: "HA & Multi-Tenancy",
      body: "PostgreSQL persistence backend with async pooling. Redis connection pool with Upstash fallback. Tenant-scoped audit, rate limiting, and decision store.",
      isNew: true,
    },
    {
      title: "Kubernetes & Helm Chart",
      body: "Production-ready Helm 3 chart with HPA, PDB, NetworkPolicy, ServiceMonitor, and ExternalSecret integration. Non-root, read-only FS, seccomp enforced.",
      isNew: true,
    },
    {
      title: "Audit Export & Observability",
      body: "4 pluggable exporters (Elasticsearch, Splunk, Webhook, Syslog) with retry/backoff/DLQ. WebSocket audit stream with JWT auth. 13 Prometheus metrics. OTel trace injection.",
      isNew: true,
    },
    {
      title: "Qdrant Semantic Layer",
      body: "Extended pattern matching via Qdrant vector store with symbolic narrowing. Fail-open design — static patterns remain the safety floor.",
      isNew: true,
    },
    {
      title: "FIPS-140 & Production Gates",
      body: "FIPS-140 compliance mode with startup validation. Production config gate enforces receipt secret, Redis, Postgres, and secret backend before launch.",
      isNew: true,
    },
    {
      title: "Deeper Input Decoding",
      body: "Base64 recursion depth increased from 5 to 10 layers with budget cap. Bidi/RTL override characters stripped. Data-URI payloads decoded inline before Base64 pass.",
    },
    {
      title: "Receipt Nonce Binding",
      body: "Every audit receipt now includes a 16-byte cryptographic nonce bound into both the HMAC signature and decision token. Identical requests produce unique receipts.",
    },
  ];

  return (
    <section
      style={{
        padding: "4rem 2rem",
        background: "var(--surface-2)",
        borderTop: "1px solid var(--border)",
        borderBottom: "1px solid var(--border)",
      }}
    >
      <div className="container">
        <div
          style={{
            display: "inline-block",
            background: "var(--crimson-glow)",
            border: "1px solid var(--crimson)",
            color: "var(--silver)",
            fontFamily: "var(--font-mono)",
            fontSize: "0.77rem",
            padding: "0.3rem 0.8rem",
            borderRadius: "100px",
            marginBottom: "1rem",
            letterSpacing: "0.05em",
          }}
        >
          v1.8 — April 2026
        </div>
        <h2
          style={{
            fontFamily: "var(--font-head)",
            fontSize: "1.75rem",
            fontWeight: 800,
            color: "var(--white)",
            marginBottom: "0.5rem",
          }}
        >
          What&apos;s New — Enterprise Edition
        </h2>
        <p
          style={{
            color: "var(--silver)",
            marginBottom: "2.5rem",
            fontSize: "1rem",
          }}
        >
          Enterprise auth, multi-tenancy, Kubernetes, and full observability stack — now production-ready.
        </p>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: "1.25rem",
          }}
        >
          {updates.map(({ title, body, isNew }) => (
            <div
              key={title}
              style={{
                background: "var(--surface)",
                border: isNew ? "1px solid var(--crimson)" : "1px solid var(--border)",
                borderLeft: isNew ? "3px solid var(--green)" : "3px solid var(--crimson)",
                borderRadius: "8px",
                padding: "1.25rem",
                position: "relative",
              }}
            >
              {isNew && (
                <span
                  style={{
                    position: "absolute",
                    top: "0.75rem",
                    right: "0.75rem",
                    background: "var(--green)",
                    color: "var(--black)",
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.62rem",
                    fontWeight: 700,
                    padding: "0.15rem 0.5rem",
                    borderRadius: "100px",
                    letterSpacing: "0.08em",
                    textTransform: "uppercase",
                  }}
                >
                  NEW
                </span>
              )}
              <h3
                style={{
                  fontSize: "0.95rem",
                  color: "var(--white)",
                  marginBottom: "0.4rem",
                  fontWeight: 600,
                }}
              >
                {title}
              </h3>
              <p
                style={{
                  fontSize: "0.85rem",
                  color: "var(--silver)",
                  lineHeight: 1.55,
                }}
              >
                {body}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Services() {
  const services = [
    {
      title: "AI Security Audit",
      desc: "Structured review of your agent architecture, action surface, and risk posture. Delivered as a written report with prioritized findings.",
    },
    {
      title: "Rapid Integration",
      desc: "Hands-on support deploying Aletheia Core into your stack. Covers policy manifest design, endpoint configuration, and API key setup.",
    },
    {
      title: "Managed Protection",
      desc: "Ongoing monitoring and policy tuning as your agent capabilities evolve. Available as a retainer engagement.",
    },
    {
      title: "Compliance Mapping",
      desc: "Map your audit receipt outputs to relevant frameworks. Supports documentation for internal controls and third-party reviews.",
    },
    {
      title: "Enterprise Self-Hosted",
      desc: "Full deployment support for air-gapped or private cloud environments. Includes architecture review and production readiness checklist.",
    },
    {
      title: "Team Training",
      desc: "Half-day or full-day sessions covering AI agent attack vectors, Aletheia policy design, and incident response playbooks.",
    },
  ];

  return (
    <section
      id="services"
      style={{ padding: "5rem 2rem", background: "var(--surface)" }}
    >
      <div className="container">
        <h2
          style={{
            fontFamily: "var(--font-head)",
            fontSize: "1.75rem",
            fontWeight: 800,
            color: "var(--white)",
            marginBottom: "0.5rem",
          }}
        >
          Services
        </h2>
        <p
          style={{
            color: "var(--silver)",
            marginBottom: "2.5rem",
            fontSize: "1rem",
          }}
        >
          Available now. Engagements are designed for teams deploying AI agents
          in production.
        </p>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
            gap: "1.25rem",
            marginBottom: "2.5rem",
          }}
        >
          {services.map(({ title, desc }) => (
            <div
              key={title}
              style={{
                background: "var(--surface-2)",
                border: "1px solid var(--border)",
                borderLeft: "3px solid var(--crimson)",
                borderRadius: "8px",
                padding: "1.25rem",
              }}
            >
              <h3
                style={{
                  fontSize: "0.97rem",
                  color: "var(--white)",
                  marginBottom: "0.4rem",
                  fontWeight: 600,
                }}
              >
                {title}
              </h3>
              <p style={{ fontSize: "0.85rem", color: "var(--silver)", lineHeight: 1.55 }}>
                {desc}
              </p>
            </div>
          ))}
        </div>
        <div style={{ textAlign: "center" }}>
          <a
            href={`mailto:${URLS.contactEmail}?subject=Service Inquiry`}
            className="btn-primary"
          >
            Book a Service →
          </a>
          <p
            style={{
              marginTop: "0.75rem",
              fontSize: "0.82rem",
              color: "var(--muted)",
            }}
          >
            {URLS.contactEmail}
          </p>
        </div>
      </div>
    </section>
  );
}

function VerifyItYourself() {
  return (
    <section style={{ padding: "4rem 2rem", background: "var(--surface)" }}>
      <div className="container" style={{ maxWidth: "720px" }}>
        <h2
          style={{
            fontFamily: "var(--font-head)",
            fontSize: "1.75rem",
            fontWeight: 800,
            color: "var(--white)",
            marginBottom: "0.75rem",
          }}
        >
          Verify it yourself
        </h2>
        <p
          style={{
            color: "var(--silver)",
            fontSize: "1rem",
            lineHeight: 1.7,
            marginBottom: "1.5rem",
          }}
        >
          You do not need to trust us. Clone the repo, run the scan, and inspect
          the signed receipt yourself.
        </p>

        <div
          style={{
            background: "var(--surface-2)",
            border: "1px solid var(--border)",
            borderRadius: "8px",
            padding: "1.25rem",
            marginBottom: "1.5rem",
            fontFamily: "var(--font-mono)",
            fontSize: "0.82rem",
            color: "var(--silver)",
            lineHeight: 1.8,
            overflowX: "auto",
          }}
        >
          <div style={{ color: "var(--muted)" }}># Clone and install</div>
          <div>git clone {URLS.github}.git</div>
          <div>cd aletheia-core &amp;&amp; pip install -r requirements.txt</div>
          <br />
          <div style={{ color: "var(--muted)" }}># Run a scan</div>
          <div>
            curl -X POST http://localhost:8000/v1/audit \
          </div>
          <div style={{ paddingLeft: "1rem" }}>
            -H &quot;Content-Type: application/json&quot; \
          </div>
          <div style={{ paddingLeft: "1rem" }}>
            -d &apos;{`{"payload":"test input","origin":"local","action":"fetch_data"}`}&apos;
          </div>
          <br />
          <div style={{ color: "var(--muted)" }}>
            # Every response includes a signed receipt you can independently
            verify
          </div>
        </div>

        <p
          style={{
            color: "var(--silver)",
            fontSize: "0.9rem",
            lineHeight: 1.6,
            marginBottom: "1.5rem",
          }}
        >
          Every decision &mdash; PROCEED or DENIED &mdash; produces an
          HMAC-SHA256 signed receipt binding the decision to the policy hash,
          payload fingerprint, action, and origin. Paste any receipt into the
          viewer to inspect its fields.
        </p>

        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <a href="/verify" className="btn-secondary">
            Open Receipt Viewer
          </a>
          <a href="/demo" className="btn-primary">
            ▶ Run Demo
          </a>
        </div>
      </div>
    </section>
  );
}
