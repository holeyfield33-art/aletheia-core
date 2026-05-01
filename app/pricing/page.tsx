import type { Metadata } from "next";
import UpgradeButton from "@/app/components/UpgradeButton";
import ROICalculator from "@/app/components/ROICalculator";
import { PRICING, PRODUCT, URLS } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "Pricing",
  description: `${PRODUCT.name} pricing — sovereign audit receipts for secure AI decisions.`,
};

function formatUsd(amount: number): string {
  return amount === 0 ? "Free" : `$${amount}`;
}

function formatReceipts(receipts: number): string {
  return receipts.toLocaleString();
}

const tiers = [
  {
    label: "Free",
    name: "Free evaluation",
    price: "Free",
    priceDetail: "/ month",
    color: "var(--silver)",
    description: `Generate up to ${formatReceipts(PRICING.free.receipts)} Sovereign Audit Receipts each month with no credit card required.`,
    features: [
      `${formatReceipts(PRICING.free.receipts)} Sovereign Audit Receipts / month`,
      "Signed receipt verification",
      "One API key",
      "7-day audit logs",
      "Evaluation access",
    ],
    cta: { label: "Start Free", href: "/dashboard/keys" },
    highlight: false,
  },
  {
    label: "Scale",
    name: "Launch tier",
    price: formatUsd(PRICING.scale.price),
    priceDetail: "/mo",
    color: "var(--crimson-hi)",
    description: `Production access for teams that need ${formatReceipts(PRICING.scale.receipts)} verified decisions each month.`,
    features: [
      `${formatReceipts(PRICING.scale.receipts)} Sovereign Audit Receipts / month`,
      "Cryptographic proof for each secured decision",
      "30-day audit logs",
      "Up to 10 API keys",
      "Priority support",
    ],
    cta: { label: "Start Scale", href: "/pricing?tier=scale" },
    highlight: true,
  },
  {
    label: "Pro",
    name: "Production tier",
    price: formatUsd(PRICING.pro.price),
    priceDetail: "/mo",
    color: "var(--white)",
    description: `Higher-throughput hosted protection for ${formatReceipts(PRICING.pro.receipts)} verified decisions each month.`,
    features: [
      `${formatReceipts(PRICING.pro.receipts)} Sovereign Audit Receipts / month`,
      "Cryptographic proof for each secured decision",
      "30-day audit logs",
      "Up to 10 API keys",
      "Priority support",
      "Webhook integrations",
    ],
    cta: { label: "Start Pro", href: "/pricing?tier=pro" },
    highlight: false,
  },
];

const faqs = [
  {
    q: "Can I self-host Aletheia Core for free?",
    a: "Yes. The core engine is MIT-licensed and always free to self-host. Hosted tiers add managed delivery, usage gates, and Stripe billing.",
  },
  {
    q: "What counts as a Sovereign Audit Receipt?",
    a: "Each verified decision that produces a signed receipt counts as one Sovereign Audit Receipt. Verification lookups do not count against your allowance.",
  },
  {
    q: "Can I upgrade or downgrade at any time?",
    a: "Yes. Upgrades take effect immediately. Downgrades take effect at the end of your current billing period.",
  },
  {
    q: "Is there a credit card required for the free trial?",
    a: "No. The free tier requires no payment method. You can generate an evaluation key instantly from the dashboard.",
  },
  {
    q: "What happens if I exceed my monthly limit?",
    a: "Free-tier usage beyond your quota returns a paid-upgrade response. Paid fixed tiers stay capped to their monthly allowance, while PAYG bills only for metered secured decisions.",
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
          Sovereign Audit Receipts for every secured decision.
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
          Start free, self-host the MIT-licensed core, or move into managed
          Scale and Pro tiers when you need verified decisions at production
          volume.
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
            {t.label === "Free" ? (
              <a
                href={t.cta.href}
                className="btn-secondary"
                style={{
                  display: "block",
                  textAlign: "center",
                  textDecoration: "none",
                }}
              >
                {t.cta.label}
              </a>
            ) : (
              <UpgradeButton
                label={t.cta.label}
                tier={t.label.toLowerCase() as "scale" | "pro"}
                className={t.highlight ? "btn-primary" : "btn-secondary"}
                style={{ width: "100%", justifyContent: "center" }}
              />
            )}
          </div>
        ))}
      </div>

      <div
        className="trust-section"
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "10px",
          padding: "1.5rem",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "1rem",
          flexWrap: "wrap",
          marginBottom: "1.5rem",
        }}
      >
        <p style={{ color: "var(--silver)", fontSize: "0.95rem", margin: 0 }}>
          Each receipt = cryptographic proof of AI safety.
        </p>
        <a
          href="/verify"
          target="_blank"
          rel="noopener noreferrer"
          className="btn-secondary"
          style={{ textDecoration: "none" }}
        >
          Verify a signed receipt →
        </a>
      </div>

      <div
        className="payg-section"
        style={{
          background: "var(--crimson-glow)",
          border: "1px solid var(--crimson)",
          borderRadius: "10px",
          padding: "1.5rem",
          marginBottom: "2rem",
        }}
      >
        <h4
          style={{
            fontFamily: "var(--font-head)",
            fontSize: "1.1rem",
            color: "var(--white)",
            marginBottom: "0.45rem",
          }}
        >
          Need flexibility?
        </h4>
        <p
          style={{
            color: "var(--silver)",
            fontSize: "0.92rem",
            marginBottom: "1rem",
          }}
        >
          ${PRICING.payg.pricePerReceipt.toFixed(5)} per receipt — pay only for
          what you use.
        </p>
        <UpgradeButton label="Enable PAYG →" tier="payg" />
      </div>

      <ROICalculator />

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
          Self-hosted core and enterprise support remain available.
        </h3>
        <p
          style={{
            color: "var(--silver)",
            fontSize: "0.9rem",
            marginBottom: "1rem",
          }}
        >
          Self-host the MIT-licensed engine, or contact us for custom policy
          engineering, red-team review, and managed deployment.
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
