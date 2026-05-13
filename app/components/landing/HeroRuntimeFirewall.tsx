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
            Block unsafe AI agent actions before they execute. Signed receipts included.
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
              gap: "1rem",
              justifyContent: "center",
              alignItems: "center",
              flexWrap: "wrap",
              marginBottom: "1.2rem",
            }}
          >
            <a className="btn-primary" href="/demo" style={{ fontSize: "1.05rem", padding: "0.9rem 1.8rem" }}>
              Try Live Demo →
            </a>
            <a className="btn-secondary" href={URLS.github} target="_blank" rel="noopener noreferrer" style={{ fontSize: "1rem", padding: "0.9rem 1.8rem" }}>
              Deploy Self-Hosted (Free)
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
              { label: "MIT Licensed" },
              { label: "Red Team Tested" },
              { label: "Ed25519 Signed" },
              { label: "1000+ Tests" },
            ].map((item) => (
              <span
                key={item.label}
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
                {item.label}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
