import type { Metadata } from "next";
import { PRODUCT, URLS } from "@/lib/site-config";
import { HOSTED_PLANS, formatPlanPrice } from "@/lib/hosted-plans";

export const metadata: Metadata = {
  title: "Pricing",
  description: `${PRODUCT.name} pricing — open-source core, hosted API, and expert services.`,
};

const tiers = [
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
      "Unlimited requests",
    ],
    cta: { label: "View on GitHub", href: URLS.github },
    highlight: false,
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
      "7-day audit logs",
      "Evaluation use only",
    ],
    cta: { label: "Start Free Trial", href: "/dashboard/keys" },
    highlight: false,
  },
  {
    label: "Hosted Pro",
    name: "Production API",
    price: formatPlanPrice(HOSTED_PLANS.PRO.monthlyPriceCents),
    priceDetail: "/mo",
    color: "var(--crimson-hi)",
    description:
      "Production API access with 50,000 requests/month, retained audit logs, and priority support.",
    features: [
      "Production API access",
      "50,000 requests / month",
      "30-day audit logs",
      "Up to 10 API keys",
      "Priority support",
      "Webhook integrations",
    ],
    cta: { label: "Upgrade to Hosted Pro", href: "/dashboard" },
    highlight: true,
  },
  {
    label: "Hosted Max",
    name: "High-throughput API",
    price: formatPlanPrice(HOSTED_PLANS.MAX.monthlyPriceCents),
    priceDetail: "/mo",
    color: "var(--white)",
    description:
      "Higher-throughput hosted API access with 200,000 requests/month for production workloads that outgrow Pro.",
    features: [
      "Production API access",
      "200,000 requests / month",
      "30-day audit logs",
      "Up to 10 API keys",
      "Priority support",
      "Webhook integrations",
    ],
    cta: { label: "Upgrade to Hosted Max", href: "/dashboard" },
    highlight: false,
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
      "Dedicated support channel",
    ],
    cta: {
      label: "Book Services",
      href: `mailto:${URLS.contactEmail}?subject=Service Inquiry`,
    },
    highlight: false,
  },
];

const faqs = [
  {
    q: "Can I self-host Aletheia Core for free?",
    a: "Yes. The core engine is MIT-licensed and always free to self-host. The hosted API is a managed convenience layer.",
  },
  {
    q: "What counts as a request?",
    a: "Each call to the /evaluate endpoint counts as one request. Manifest verification and audit log reads do not count against your quota.",
  },
  {
    q: "Can I upgrade or downgrade at any time?",
    a: "Yes. Upgrades take effect immediately. Downgrades take effect at the end of your current billing period.",
  },
  {
    q: "Is there a credit card required for the free trial?",
    a: "No. The Hosted Trial tier requires no payment method. You can generate an evaluation key instantly from the dashboard.",
  },
  {
    q: "What happens if I exceed my monthly limit?",
    a: "Requests beyond your quota receive a 429 response with a Retry-After header. No overage charges — upgrade when you're ready.",
  },
  {
    q: "Do you offer annual billing?",
    a: "Not yet. Contact us if you'd like to discuss annual or enterprise pricing.",
  },
];

export default function PricingPage() {
  return (
    <div
      style={{
        maxWidth: "960px",
        margin: "0 auto",
        padding: "4rem 2rem 5rem",
      }}
    >
      <div style={{ textAlign: "center", marginBottom: "3rem" }}>
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
          Pricing
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
          Open-source core. Hosted API for production.
        </h1>
        <p
          style={{
            color: "var(--silver)",
            fontSize: "1.05rem",
            maxWidth: "540px",
            margin: "0 auto",
            lineHeight: 1.65,
          }}
        >
          Start free with the self-hosted engine or an evaluation key.
          Upgrade to Hosted Pro when you need production throughput.
          Choose Max when you need 200,000 calls/month.
        </p>
      </div>

      {/* Tier cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))",
          gap: "1.25rem",
          marginBottom: "4rem",
        }}
      >
        {tiers.map((t) => (
          <div
            key={t.name}
            style={{
              background: t.highlight ? "var(--surface-2)" : "var(--surface)",
              border: t.highlight
                ? "1px solid var(--crimson)"
                : "1px solid var(--border)",
              borderRadius: "10px",
              padding: "1.75rem",
              display: "flex",
              flexDirection: "column",
              gap: "1rem",
              position: "relative",
            }}
          >
            {t.highlight && (
              <div
                style={{
                  position: "absolute",
                  top: "-10px",
                  left: "50%",
                  transform: "translateX(-50%)",
                  background: "var(--crimson-hi)",
                  color: "var(--white)",
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.65rem",
                  letterSpacing: "0.08em",
                  padding: "0.2rem 0.7rem",
                  borderRadius: "100px",
                  textTransform: "uppercase",
                }}
              >
                Most Popular
              </div>
            )}
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
                  {t.name}
                </h3>
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.72rem",
                    color: t.color,
                    letterSpacing: "0.06em",
                  }}
                >
                  {t.label}
                </span>
              </div>
              <div style={{ marginBottom: "0.5rem" }}>
                <span
                  style={{
                    fontFamily: "var(--font-head)",
                    fontSize: "1.5rem",
                    fontWeight: 800,
                    color: "var(--white)",
                  }}
                >
                  {t.price}
                </span>
                {t.priceDetail && (
                  <span
                    style={{
                      color: "var(--muted)",
                      fontSize: "0.82rem",
                      marginLeft: "0.3rem",
                    }}
                  >
                    {t.priceDetail}
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
                {t.description}
              </p>
            </div>
            <ul style={{ listStyle: "none", flex: 1, padding: 0, margin: 0 }}>
              {t.features.map((f) => (
                <li
                  key={f}
                  style={{
                    display: "flex",
                    gap: "0.6rem",
                    padding: "0.4rem 0",
                    fontSize: "0.87rem",
                    color: "var(--silver)",
                    alignItems: "flex-start",
                  }}
                >
                  <span style={{ color: t.color, flexShrink: 0 }}>✓</span>
                  {f}
                </li>
              ))}
            </ul>
            <a
              href={t.cta.href}
              className={t.highlight ? "btn-primary" : "btn-secondary"}
              style={{
                display: "block",
                textAlign: "center",
                textDecoration: "none",
              }}
            >
              {t.cta.label}
            </a>
          </div>
        ))}
      </div>

      {/* FAQ */}
      <div style={{ maxWidth: "680px", margin: "0 auto" }}>
        <h2
          style={{
            fontFamily: "var(--font-head)",
            fontSize: "1.4rem",
            fontWeight: 800,
            color: "var(--white)",
            marginBottom: "1.5rem",
            textAlign: "center",
          }}
        >
          Frequently Asked Questions
        </h2>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "0",
          }}
        >
          {faqs.map((faq) => (
            <div
              key={faq.q}
              style={{
                padding: "1.25rem 0",
                borderBottom: "1px solid var(--border)",
              }}
            >
              <h3
                style={{
                  fontFamily: "var(--font-head)",
                  fontSize: "0.95rem",
                  fontWeight: 700,
                  color: "var(--white)",
                  marginBottom: "0.4rem",
                }}
              >
                {faq.q}
              </h3>
              <p
                style={{
                  color: "var(--silver)",
                  fontSize: "0.88rem",
                  lineHeight: 1.6,
                  margin: 0,
                }}
              >
                {faq.a}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* CTA banner */}
      <div
        style={{
          marginTop: "3rem",
          background: "var(--crimson-glow)",
          border: "1px solid var(--crimson)",
          borderRadius: "10px",
          padding: "2rem",
          textAlign: "center",
        }}
      >
        <h3
          style={{
            fontFamily: "var(--font-head)",
            fontSize: "1.15rem",
            fontWeight: 700,
            color: "var(--white)",
            marginBottom: "0.5rem",
          }}
        >
          Need enterprise-grade deployment?
        </h3>
        <p
          style={{
            color: "var(--silver)",
            fontSize: "0.9rem",
            marginBottom: "1rem",
          }}
        >
          Custom policy engineering, agent red-team review, and managed deployment.
        </p>
        <a
          href={`mailto:${URLS.contactEmail}?subject=Enterprise Inquiry`}
          className="btn-primary"
          style={{ textDecoration: "none" }}
        >
          Contact Us
        </a>
      </div>
    </div>
  );
}
