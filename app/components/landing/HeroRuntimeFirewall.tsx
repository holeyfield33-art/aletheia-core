import Link from "next/link";
import { URLS } from "@/lib/site-config";

export default function HeroRuntimeFirewall() {
  return (
    <section
      style={{
        padding: "4.75rem 1.5rem 3rem",
        background:
          "radial-gradient(circle at top, rgba(176, 34, 54, 0.16), transparent 45%), linear-gradient(180deg, rgba(8,10,12,1) 0%, rgba(14,17,21,1) 100%)",
      }}
    >
      <div className="container" style={{ maxWidth: "1120px" }}>
        <div
          style={{
            maxWidth: "820px",
            margin: "0 auto",
            textAlign: "center",
          }}
        >
          <div
            style={{
              display: "inline-block",
              border: "1px solid var(--crimson)",
              background: "var(--crimson-glow)",
              color: "var(--silver)",
              borderRadius: "999px",
              padding: "0.3rem 0.8rem",
              fontFamily: "var(--font-mono)",
              fontSize: "0.74rem",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              marginBottom: "1.2rem",
            }}
          >
            AI Agent Runtime Firewall
          </div>

          <h1
            className="hero-page-h1"
            style={{
              fontFamily: "var(--font-head)",
              fontSize: "clamp(2.4rem, 6vw, 4.3rem)",
              lineHeight: 1.02,
              color: "var(--white)",
              marginBottom: "1rem",
            }}
          >
            AI Agent Runtime Firewall
          </h1>

          <p
            style={{
              color: "var(--silver)",
              fontSize: "1.15rem",
              lineHeight: 1.7,
              maxWidth: "720px",
              margin: "0 auto 0.8rem",
            }}
          >
            Watch the attack. Watch the agent. Watch Aletheia block the action
            before execution.
          </p>

          <p
            style={{
              color: "var(--muted)",
              fontSize: "0.98rem",
              lineHeight: 1.75,
              maxWidth: "760px",
              margin: "0 auto 1.6rem",
            }}
          >
            Aletheia Core audits high-risk AI agent decisions before agents read
            secrets, run shell commands, modify configs, send data externally,
            or touch production workflows. Every verdict can generate a
            tamper-evident receipt.
          </p>

          <div
            className="hero-cta-stack"
            style={{
              display: "flex",
              gap: "0.8rem",
              justifyContent: "center",
              alignItems: "center",
              flexWrap: "wrap",
              marginBottom: "1.2rem",
            }}
          >
            <Link className="btn-primary" href="/auth/register?callbackUrl=%2Fdashboard">
              Protect My Agent
            </Link>
            <Link className="btn-secondary" href="/demo">
              Run Live Demo
            </Link>
            <a
              href={URLS.github}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: "var(--silver)", textDecoration: "none", fontWeight: 600 }}
            >
              View GitHub
            </a>
          </div>

          <p
            style={{
              color: "var(--muted)",
              fontFamily: "var(--font-mono)",
              fontSize: "0.82rem",
              lineHeight: 1.8,
              marginBottom: "1.4rem",
            }}
          >
            Watch the attack. Watch the agent. Watch Aletheia stop it. Verify the receipt. Protect your own system.
          </p>

          <div
            style={{
              display: "flex",
              justifyContent: "center",
              flexWrap: "wrap",
              gap: "0.75rem",
            }}
          >
            {[
              "Open-source core",
              "Hosted API",
              "Signed receipts",
              "Red-team tested",
            ].map((item) => (
              <span
                key={item}
                style={{
                  background: "var(--surface)",
                  border: "1px solid var(--border-hi)",
                  color: "var(--silver)",
                  borderRadius: "999px",
                  padding: "0.35rem 0.85rem",
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.74rem",
                }}
              >
                {item}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
