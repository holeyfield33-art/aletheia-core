import Link from "next/link";

export default function FinalCTA() {
  return (
    <section style={{ padding: "0 1.5rem 4rem" }}>
      <div className="container" style={{ maxWidth: "1120px" }}>
        <div
          style={{
            border: "1px solid var(--crimson)",
            background:
              "linear-gradient(180deg, rgba(176,34,54,0.12), rgba(14,17,21,1))",
            borderRadius: "18px",
            padding: "2rem",
            textAlign: "center",
          }}
        >
          <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.74rem", color: "var(--silver)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "0.6rem" }}>
            Final step
          </div>
          <h2 style={{ fontFamily: "var(--font-head)", fontSize: "clamp(1.8rem, 4vw, 2.6rem)", color: "var(--white)", marginBottom: "0.75rem" }}>
            Protect your agent before it acts.
          </h2>
          <p style={{ color: "var(--silver)", maxWidth: "760px", margin: "0 auto 1.2rem", lineHeight: 1.7 }}>
            Use Aletheia Core to preflight risky prompts, tool calls, and agent decisions before they touch files, secrets, APIs, money, or production systems.
          </p>
          <div className="hero-cta-stack" style={{ display: "flex", gap: "0.8rem", justifyContent: "center", flexWrap: "wrap" }}>
            <Link className="btn-primary" href="/auth/register?callbackUrl=%2Fdashboard">
              Protect My Agent
            </Link>
            <Link className="btn-secondary" href="/demo">
              Run Live Demo
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
