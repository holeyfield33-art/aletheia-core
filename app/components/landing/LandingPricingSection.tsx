import Link from "next/link";
import { PRICING, URLS } from "@/lib/site-config";

type PricingCard = {
  name: string;
  price: string;
  detail: string;
  description: string;
  ctaLabel: string;
  ctaHref: string;
  external?: boolean;
};

const pricingCards: PricingCard[] = [
  {
    name: "Free",
    price: "Free",
    detail: `${PRICING.free.receipts.toLocaleString()} receipts / month`,
    description: "Open-source evaluation path with the existing free receipt allowance.",
    ctaLabel: "Deploy Aletheia Core",
    ctaHref: URLS.github,
    external: true,
  },
  {
    name: "Scale",
    price: `$${PRICING.scale.price}`,
    detail: `${PRICING.scale.receipts.toLocaleString()} receipts / month`,
    description: "Hosted protection for teams moving into production workflows.",
    ctaLabel: "Protect My Agent",
    ctaHref: "/pricing?tier=scale",
    external: false,
  },
  {
    name: "Pro",
    price: `$${PRICING.pro.price}`,
    detail: `${PRICING.pro.receipts.toLocaleString()} receipts / month`,
    description: "Higher-throughput hosted runtime firewall coverage.",
    ctaLabel: "Protect My Agent",
    ctaHref: "/pricing?tier=pro",
    external: false,
  },
  {
    name: "PAYG",
    price: `$${PRICING.payg.pricePerReceipt.toFixed(5)}`,
    detail: "Per secured decision",
    description: "Existing metered path for exact usage without changing your billing model.",
    ctaLabel: "Protect My Agent",
    ctaHref: "/pricing",
    external: false,
  },
];

export default function LandingPricingSection() {
  return (
    <section id="pricing" style={{ padding: "0 1.5rem 2.25rem" }}>
      <div className="container" style={{ maxWidth: "1120px" }}>
        <div style={{ marginBottom: "1rem" }}>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.74rem", color: "var(--muted)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "0.6rem" }}>
            Step 5
          </div>
          <h2 style={{ fontFamily: "var(--font-head)", fontSize: "clamp(1.7rem, 4vw, 2.4rem)", color: "var(--white)", marginBottom: "0.7rem" }}>
            Choose the path that fits your deployment.
          </h2>
          <p style={{ color: "var(--silver)", lineHeight: 1.7, maxWidth: "760px" }}>
            The pricing model stays exactly the same. This section only sharpens the path from evaluation to hosted protection.
          </p>
        </div>

        <div className="pricing-grid" style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: "1rem", marginBottom: "1rem" }}>
          {pricingCards.map((card) => (
            <article
              key={card.name}
              style={{
                background: card.name === "Scale" ? "var(--surface-2)" : "var(--surface)",
                border: card.name === "Scale" ? "1px solid var(--crimson)" : "1px solid var(--border)",
                borderRadius: "14px",
                padding: "1.25rem",
                display: "grid",
                gap: "0.8rem",
              }}
            >
              <div>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.74rem", color: "var(--muted)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "0.35rem" }}>
                  {card.name}
                </div>
                <div style={{ fontFamily: "var(--font-head)", fontSize: "1.6rem", color: "var(--white)", marginBottom: "0.25rem" }}>
                  {card.price}
                </div>
                <div style={{ color: "var(--silver)", fontFamily: "var(--font-mono)", fontSize: "0.78rem" }}>
                  {card.detail}
                </div>
              </div>
              <p style={{ color: "var(--silver)", lineHeight: 1.65 }}>{card.description}</p>
              {card.external ? (
                <a className="btn-secondary" href={card.ctaHref} target="_blank" rel="noopener noreferrer">
                  {card.ctaLabel}
                </a>
              ) : (
                <Link className={card.name === "Free" ? "btn-secondary" : "btn-primary"} href={card.ctaHref}>
                  {card.ctaLabel}
                </Link>
              )}
            </article>
          ))}
        </div>

        <article
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "14px",
            padding: "1.25rem",
            display: "flex",
            justifyContent: "space-between",
            gap: "1rem",
            flexWrap: "wrap",
            alignItems: "center",
          }}
        >
          <div>
            <div style={{ fontFamily: "var(--font-head)", fontSize: "1.25rem", color: "var(--white)", marginBottom: "0.35rem" }}>
              Need a guided review first?
            </div>
            <div style={{ color: "var(--silver)", lineHeight: 1.6 }}>
              Use the existing mini-audit offer before you deploy or buy hosted protection.
            </div>
          </div>
          <a className="btn-primary" href="mailto:info@aletheia-core.com?subject=Mini%20Audit%20Request">
            Book Mini Audit
          </a>
        </article>
      </div>
    </section>
  );
}
