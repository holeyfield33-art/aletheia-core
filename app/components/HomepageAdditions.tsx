import { SEO_SOLUTIONS } from "@/lib/site-config";

const protectedAgents = [
  {
    title: "Finance Agent Template",
    copy: "Dual-step approval and restricted action lists for transfer and disbursement workflows.",
  },
  {
    title: "DevOps Agent Template",
    copy: "Sandbox-first command policy for deployment tooling, shell execution, and infra drift actions.",
  },
  {
    title: "Support Agent Template",
    copy: "PII-redacting response contracts and outbound egress constraints for user-facing assistants.",
  },
];

export default function HomepageAdditions() {
  return (
    <section className="home-additions-shell" style={{ padding: "4rem 2rem" }}>
      <div className="container" style={{ maxWidth: "980px" }}>
        <article
          style={{
            border: "1px solid var(--crimson)",
            background: "linear-gradient(150deg, var(--surface), var(--surface-2))",
            borderRadius: "12px",
            padding: "1.35rem",
            marginBottom: "1.2rem",
          }}
        >
          <h2 style={{ fontFamily: "var(--font-head)", fontSize: "1.35rem", marginBottom: "0.35rem" }}>
            Mini Audit
          </h2>
          <p style={{ color: "var(--silver)", maxWidth: "720px", marginBottom: "0.85rem" }}>
            Run a guided 5-minute threat triage against your current agent runtime and export a practical first-pass hardening list.
          </p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem" }}>
            <a className="btn-primary" href="/demo">
              Run Mini Audit
            </a>
            <a className="btn-secondary" href="/verify">
              Verify Existing Receipt
            </a>
          </div>
        </article>

        <article
          style={{
            border: "1px solid var(--border)",
            background: "var(--surface)",
            borderRadius: "12px",
            padding: "1.35rem",
            marginBottom: "1.2rem",
          }}
        >
          <h2 style={{ fontFamily: "var(--font-head)", fontSize: "1.35rem", marginBottom: "0.35rem" }}>
            Protected Agent Templates
          </h2>
          <p style={{ color: "var(--silver)", marginBottom: "0.8rem" }}>
            Pre-scoped policy templates designed to cut rollout time for common enterprise agent classes.
          </p>
          <div className="home-additions-grid" style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: "0.8rem" }}>
            {protectedAgents.map((agent) => (
              <div
                key={agent.title}
                style={{
                  border: "1px solid var(--border-hi)",
                  background: "var(--surface-2)",
                  borderRadius: "8px",
                  padding: "0.85rem",
                }}
              >
                <h3 style={{ fontFamily: "var(--font-head)", fontSize: "0.98rem", marginBottom: "0.25rem" }}>
                  {agent.title}
                </h3>
                <p style={{ color: "var(--muted)", fontSize: "0.84rem", lineHeight: 1.55 }}>{agent.copy}</p>
              </div>
            ))}
          </div>
        </article>

        <article id="explore-aletheia" style={{ border: "1px solid var(--border)", background: "var(--surface)", borderRadius: "12px", padding: "1.35rem" }}>
          <h2 style={{ fontFamily: "var(--font-head)", fontSize: "1.35rem", marginBottom: "0.35rem" }}>
            Explore Aletheia
          </h2>
          <p style={{ color: "var(--silver)", marginBottom: "0.8rem" }}>
            Deep-dive pages for teams evaluating runtime audit controls and enterprise guardrail patterns.
          </p>
          <div className="home-additions-grid" style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: "0.8rem" }}>
            {SEO_SOLUTIONS.map((entry) => (
              <a
                key={entry.href}
                href={entry.href}
                style={{
                  border: "1px solid var(--border-hi)",
                  background: "var(--surface-2)",
                  borderRadius: "8px",
                  padding: "0.85rem",
                  textDecoration: "none",
                }}
              >
                <h3 style={{ fontFamily: "var(--font-head)", fontSize: "0.98rem", color: "var(--white)", marginBottom: "0.25rem" }}>
                  {entry.title}
                </h3>
                <p style={{ color: "var(--muted)", fontSize: "0.84rem", lineHeight: 1.55 }}>{entry.summary}</p>
              </a>
            ))}
          </div>
        </article>
      </div>
    </section>
  );
}
