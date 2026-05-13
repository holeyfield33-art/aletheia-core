import type { Metadata } from "next";
import HeroRuntimeFirewall from "@/app/components/landing/HeroRuntimeFirewall";
import SocialProofBar from "@/app/components/landing/SocialProofBar";
import RedTeamDemoSection from "@/app/components/landing/RedTeamDemoSection";
import TraderAgentDemoSection from "@/app/components/landing/TraderAgentDemoSection";
import LiveAletheiaDemoSection from "@/app/components/landing/LiveAletheiaDemoSection";
import ReceiptVerificationFlipCard from "@/app/components/landing/ReceiptVerificationFlipCard";
import LandingPricingSection from "@/app/components/landing/LandingPricingSection";
import FinalCTA from "@/app/components/landing/FinalCTA";
import ExitIntentPopup from "@/app/components/landing/ExitIntentPopup";
import { PRODUCT } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "AI Agent Runtime Firewall",
  description:
    "Aletheia Core audits high-risk AI agent decisions before agents read secrets, run shell commands, or send data externally. Every verdict generates a tamper-evident receipt.",
  alternates: { canonical: "https://aletheia-core.com" },
  openGraph: {
    title: "AI Agent Runtime Firewall | Aletheia Core",
    description: "Pre-execution AI agent security with signed receipts.",
    url: "https://aletheia-core.com",
    type: "website",
  },
};

export default function HomePage() {
  return (
    <>
      <HeroRuntimeFirewall />
      <SocialProofBar />
      <RedTeamDemoSection />
      <TraderAgentDemoSection videoUrl={process.env.NEXT_PUBLIC_TRADER_DEMO_VIDEO_URL} />
      <LiveAletheiaDemoSection />
      <ReceiptVerificationFlipCard />
      <LandingPricingSection />
      <section style={{ padding: "0 clamp(0.95rem, 4vw, 1.5rem) 2.25rem" }}>
        <div className="container" style={{ maxWidth: "1120px" }}>
          <div style={{ marginBottom: "1rem" }}>
            <h2
              style={{
                fontFamily: "var(--font-head)",
                fontSize: "clamp(1.7rem, 4vw, 2.4rem)",
                color: "var(--white)",
                marginBottom: "0.65rem",
                lineHeight: 1.2,
              }}
            >
              Protected Agent Templates
            </h2>
            <p style={{ color: "var(--silver)", lineHeight: 1.7, maxWidth: "760px" }}>
              Premade protected agents with human approval, signed decisions, and
              audit trails.
            </p>
          </div>

          <div
            className="protected-agent-grid"
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
              gap: "1rem",
            }}
          >
            <article
              style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: "14px",
                padding: "clamp(1rem, 3.2vw, 1.25rem)",
                display: "grid",
                gap: "0.75rem",
              }}
            >
              <h3
                style={{
                  fontFamily: "var(--font-head)",
                  fontSize: "clamp(1.08rem, 3.8vw, 1.3rem)",
                  color: "var(--white)",
                  lineHeight: 1.2,
                }}
              >
                Protected Support Agent
              </h3>
              <p style={{ color: "var(--silver)", lineHeight: 1.65 }}>
                Tiered customer support workflow with approval gates and signed
                decision receipts.
              </p>
              <div>
                <div style={{ fontFamily: "var(--font-head)", fontSize: "1.4rem", color: "var(--white)", marginBottom: "0.25rem" }}>
                  $49.99/mo
                </div>
                <p style={{ color: "var(--muted)", fontSize: "0.75rem", marginBottom: "0.75rem" }}>
                  Custom manifest available on request
                </p>
                <a className="btn-secondary" href="mailto:info@aletheia-core.com?subject=Protected Support Agent Request" style={{ width: "100%", textAlign: "center" }}>
                  Get Started
                </a>
              </div>
            </article>

            <article
              style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: "14px",
                padding: "clamp(1rem, 3.2vw, 1.25rem)",
                display: "grid",
                gap: "0.75rem",
              }}
            >
              <h3
                style={{
                  fontFamily: "var(--font-head)",
                  fontSize: "clamp(1.08rem, 3.8vw, 1.3rem)",
                  color: "var(--white)",
                  lineHeight: 1.2,
                }}
              >
                Protected Outreach Agent
              </h3>
              <p style={{ color: "var(--silver)", lineHeight: 1.65 }}>
                Safer outbound prospecting flows with policy checks before each
                send and signed evidence after each verdict.
              </p>
              <div>
                <div style={{ fontFamily: "var(--font-head)", fontSize: "1.4rem", color: "var(--white)", marginBottom: "0.25rem" }}>
                  $49.99/mo
                </div>
                <p style={{ color: "var(--muted)", fontSize: "0.75rem", marginBottom: "0.75rem" }}>
                  Custom manifest available on request
                </p>
                <a className="btn-secondary" href="mailto:info@aletheia-core.com?subject=Protected Outreach Agent Request" style={{ width: "100%", textAlign: "center" }}>
                  Get Started
                </a>
              </div>
            </article>

            <article
              style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: "14px",
                padding: "clamp(1rem, 3.2vw, 1.25rem)",
                display: "grid",
                gap: "0.75rem",
              }}
            >
              <h3
                style={{
                  fontFamily: "var(--font-head)",
                  fontSize: "clamp(1.08rem, 3.8vw, 1.3rem)",
                  color: "var(--white)",
                  lineHeight: 1.2,
                }}
              >
                Protected Trading Signal Agent
              </h3>
              <p style={{ color: "var(--silver)", lineHeight: 1.65 }}>
                Paper-trading signal workflow with explicit review controls,
                risk-gated decisions, and verifiable audit trails.
              </p>
              <div>
                <div style={{ fontFamily: "var(--font-head)", fontSize: "1.4rem", color: "var(--white)", marginBottom: "0.25rem" }}>
                  $49.99/mo
                </div>
                <p style={{ color: "var(--muted)", fontSize: "0.75rem", marginBottom: "0.75rem" }}>
                  Custom manifest available on request
                </p>
                <a
                  className="btn-secondary"
                  href="https://trader.aletheia-core.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ width: "100%", textAlign: "center" }}
                >
                  Get Started
                </a>
              </div>
            </article>
          </div>
        </div>
      </section>
      <FinalCTA />
      <section
        style={{
          padding: "0 clamp(0.95rem, 4vw, 1.5rem) clamp(2.25rem, 7vw, 4rem)",
          textAlign: "center",
        }}
      >
        <div
          style={{
            color: "var(--muted)",
            fontFamily: "var(--font-mono)",
            fontSize: "0.76rem",
          }}
        >
          {PRODUCT.name} &middot; Protect your agent before it acts.
        </div>
      </section>
      <ExitIntentPopup enabled={true} />
    </>
  );
}
