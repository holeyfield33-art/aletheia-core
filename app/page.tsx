import { PRODUCT, URLS, STATUS, CTAS } from "@/lib/site-config";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AI Runtime Security for Agents",
  description:
    "Aletheia Core — AI runtime security engine. Block unsafe agent actions before execution. Signed audit receipts. Self-hosted or hosted.",
  alternates: { canonical: URLS.appBase },
};

export default function HomePage() {
  return (
    <>
      <Hero />
      <hr style={{ border: "none", borderTop: "1px solid var(--border)" }} />
      <HowItWorks />
      <hr style={{ border: "none", borderTop: "1px solid var(--border)" }} />
      <WhatItIsAndIsNot />
      <hr style={{ border: "none", borderTop: "1px solid var(--border)" }} />
      <Pricing />
      <hr style={{ border: "none", borderTop: "1px solid var(--border)" }} />
      <Services />
      <hr style={{ border: "none", borderTop: "1px solid var(--border)" }} />
      <VerifySection />
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
        {PRODUCT.testCount} Tests Passing
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
        Runtime Security for{" "}
        <em style={{ color: "var(--crimson-hi)", fontStyle: "normal" }}>
          AI Agents
        </em>
        <br />
        and Automations
      </h1>

      <p
        style={{
          fontSize: "1.05rem",
          color: "var(--silver)",
          maxWidth: "580px",
          margin: "0 auto 1.25rem",
          lineHeight: 1.7,
        }}
      >
        Block unsafe actions before execution. Every decision produces a{" "}
        <strong style={{ color: "var(--white)" }}>signed audit receipt</strong>{" "}
        for independent verification. Deploy self-hosted or consume as a hosted
        API.
      </p>

      <ul
        style={{
          listStyle: "none",
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          gap: "0.5rem",
          marginBottom: "2.5rem",
        }}
      >
        {[
          "Runtime enforcement",
          "Signed audit receipts",
          "Self-hosted or hosted",
          "Open-source MIT core",
        ].map((item) => (
          <li
            key={item}
            style={{
              background: "var(--surface-2)",
              border: "1px solid var(--border-hi)",
              padding: "0.35rem 0.85rem",
              borderRadius: "100px",
              fontFamily: "var(--font-mono)",
              fontSize: "0.78rem",
              color: "var(--silver)",
            }}
          >
            {item}
          </li>
        ))}
      </ul>

      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          gap: "0.75rem",
          alignItems: "center",
        }}
      >
        <a href={CTAS.primary.href} className="btn-primary">
          ▶ {CTAS.primary.label}
        </a>
        <a href={CTAS.services.href} className="btn-secondary">
          {CTAS.services.label}
        </a>
        <a href="/#pricing" className="btn-ghost">
          View Pricing
        </a>
      </div>

      <p
        style={{
          marginTop: "1.25rem",
          fontSize: "0.8rem",
          color: "var(--muted)",
        }}
      >
        or browse the source at{" "}
        <a
          href={URLS.github}
          style={{ color: "var(--silver-dim)" }}
          target="_blank"
          rel="noopener noreferrer"
        >
          github.com/holeyfield33-art/aletheia-core
        </a>
      </p>
    </section>
  );
}

function HowItWorks() {
  const stages = [
    {
      num: "STAGE 1",
      title: "Input Hardening",
      body: "NFKC homoglyph collapse, zero-width strip, recursive Base64 decode (up to 5 layers, 10× size-bomb protection), and URL decode — all applied before any agent sees the payload.",
    },
    {
      num: "STAGE 2",
      title: "Tri-Agent Analysis",
      body: "Scout scores threat context and detects swarm probing. Nitpicker runs semantic similarity against blocked patterns. Judge verifies the Ed25519 manifest and applies cosine-similarity veto.",
    },
    {
      num: "STAGE 3",
      title: "Signed Audit Receipt",
      body: "Every decision — PROCEED or DENIED — produces an HMAC-SHA256 signed receipt binding the decision to the policy hash, payload fingerprint, action, and origin.",
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
          How It Works
        </h2>
        <p
          style={{
            color: "var(--silver)",
            marginBottom: "2.5rem",
            fontSize: "1rem",
          }}
        >
          Every request passes three sequential stages before a decision is
          made.
        </p>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
            gap: "1.5rem",
          }}
        >
          {stages.map(({ num, title, body }) => (
            <div
              key={num}
              style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: "8px",
                padding: "1.5rem",
              }}
            >
              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.72rem",
                  color: "var(--crimson-hi)",
                  letterSpacing: "0.1em",
                  marginBottom: "0.5rem",
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
      </div>
    </section>
  );
}

function WhatItIsAndIsNot() {
  const is = [
    "Runtime enforcement layer — gates risky agent actions before execution",
    "Signed audit evidence — every decision produces a tamper-evident receipt",
    "Deployable as self-hosted service or consumed via hosted API",
    "One layer in a broader security stack",
  ];
  const isNot = [
    "Not a replacement for model alignment",
    "Does not secure infrastructure outside its deployment boundary",
    "Does not prevent all possible misuse — designed to raise the cost of attacks",
    "Not a compliance certification — consult qualified counsel for compliance",
  ];

  return (
    <section style={{ padding: "4rem 2rem", background: "var(--surface)" }}>
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
          What Aletheia Is and Is Not
        </h2>
        <p
          style={{
            color: "var(--silver)",
            marginBottom: "2.5rem",
            fontSize: "1rem",
          }}
        >
          Clarity on scope reduces integration mistakes and overclaims.
        </p>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
            gap: "2rem",
          }}
        >
          <div>
            <h3
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "0.82rem",
                color: "var(--green)",
                letterSpacing: "0.1em",
                textTransform: "uppercase",
                marginBottom: "1rem",
              }}
            >
              It is
            </h3>
            <ul style={{ listStyle: "none" }}>
              {is.map((item) => (
                <li
                  key={item}
                  style={{
                    display: "flex",
                    gap: "0.75rem",
                    padding: "0.65rem 0",
                    borderBottom: "1px solid var(--border)",
                    fontSize: "0.9rem",
                    color: "var(--silver)",
                    lineHeight: 1.55,
                  }}
                >
                  <span style={{ color: "var(--green)", flexShrink: 0, marginTop: "2px" }}>
                    ✓
                  </span>
                  {item}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "0.82rem",
                color: "var(--crimson-hi)",
                letterSpacing: "0.1em",
                textTransform: "uppercase",
                marginBottom: "1rem",
              }}
            >
              It is not
            </h3>
            <ul style={{ listStyle: "none" }}>
              {isNot.map((item) => (
                <li
                  key={item}
                  style={{
                    display: "flex",
                    gap: "0.75rem",
                    padding: "0.65rem 0",
                    borderBottom: "1px solid var(--border)",
                    fontSize: "0.9rem",
                    color: "var(--silver)",
                    lineHeight: 1.55,
                  }}
                >
                  <span style={{ color: "var(--crimson-hi)", flexShrink: 0, marginTop: "2px" }}>
                    ✕
                  </span>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}

function Pricing() {
  const plans = [
    {
      name: "Developer",
      price: "Free",
      priceDetail: "self-hosted",
      tag: "Open Source",
      tagColor: "var(--green)",
      description:
        "MIT-licensed core. Run it yourself. Full source, full control.",
      features: [
        "Full MIT source code",
        "FastAPI REST endpoint",
        "Ed25519 manifest signing",
        "HMAC-signed audit receipts",
        "Tri-agent pipeline",
        "In-memory rate limiting",
        "Community support via GitHub",
      ],
      cta: { label: "View on GitHub", href: URLS.github },
      ctaStyle: "secondary",
    },
    {
      name: "Pro",
      price: "Hosted API",
      priceDetail: STATUS.hostedApiLabel,
      tag: "Live",
      tagColor: "var(--green)",
      description:
        "Consume Aletheia as a hosted API. No infrastructure to manage.",
      features: [
        "Hosted REST endpoint",
        "Managed uptime",
        "API key provisioning",
        "Usage-based billing",
        "Email support",
        "Upstash Redis rate limiting",
        "Receipt verification endpoint",
      ],
      cta: {
        label: "Contact for Access",
        href: `mailto:${URLS.contactEmail}?subject=Hosted API Access`,
      },
      ctaStyle: "primary",
      highlight: true,
    },
    {
      name: "Enterprise",
      price: "Custom",
      priceDetail: "contact for pricing",
      tag: "Services Available",
      tagColor: "var(--silver)",
      description:
        "Self-hosted deployment with support, custom policy design, and SLA options.",
      features: [
        "Everything in Developer",
        "Integration architecture review",
        "Custom policy manifest design",
        "Managed deployment support",
        "Dedicated security engineering",
        "Audit and compliance guidance",
        "SLA options available",
      ],
      cta: {
        label: "Book a Service",
        href: `mailto:${URLS.contactEmail}?subject=Enterprise Inquiry`,
      },
      ctaStyle: "secondary",
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
          Open-source core. Hosted API live. Services available now.
        </p>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
            gap: "1.5rem",
          }}
        >
          {plans.map((plan) => (
            <div
              key={plan.name}
              style={{
                background: plan.highlight
                  ? "var(--surface-2)"
                  : "var(--surface)",
                border: plan.highlight
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
                    {plan.name}
                  </h3>
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.72rem",
                      color: plan.tagColor,
                      letterSpacing: "0.06em",
                    }}
                  >
                    {plan.tag}
                  </span>
                </div>
                <div>
                  <span
                    style={{
                      fontFamily: "var(--font-head)",
                      fontSize: "1.5rem",
                      fontWeight: 800,
                      color: "var(--white)",
                    }}
                  >
                    {plan.price}
                  </span>
                  <span
                    style={{
                      color: "var(--muted)",
                      fontSize: "0.82rem",
                      marginLeft: "0.4rem",
                    }}
                  >
                    / {plan.priceDetail}
                  </span>
                </div>
                <p
                  style={{
                    color: "var(--silver)",
                    fontSize: "0.88rem",
                    lineHeight: 1.55,
                    marginTop: "0.5rem",
                  }}
                >
                  {plan.description}
                </p>
              </div>
              <ul style={{ listStyle: "none", flex: 1 }}>
                {plan.features.map((f) => (
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
                href={plan.cta.href}
                className={
                  plan.ctaStyle === "primary" ? "btn-primary" : "btn-secondary"
                }
                style={{
                  justifyContent: "center",
                  textAlign: "center",
                  marginTop: "0.5rem",
                }}
              >
                {plan.cta.label}
              </a>
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

function VerifySection() {
  return (
    <section style={{ padding: "4rem 2rem" }}>
      <div className="container" style={{ textAlign: "center" }}>
        <h2
          style={{
            fontFamily: "var(--font-head)",
            fontSize: "1.75rem",
            fontWeight: 800,
            color: "var(--white)",
            marginBottom: "0.75rem",
          }}
        >
          Verify a Receipt
        </h2>
        <p
          style={{
            color: "var(--silver)",
            maxWidth: "520px",
            margin: "0 auto 1.75rem",
            fontSize: "1rem",
          }}
        >
          Signed receipts enable independent verification. Paste any audit
          receipt to inspect its fields and structure.
        </p>
        <a href="/verify" className="btn-secondary">
          Open Receipt Viewer →
        </a>
      </div>
    </section>
  );
}
