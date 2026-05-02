type TraderAgentDemoSectionProps = {
  videoUrl?: string;
};

export default function TraderAgentDemoSection({ videoUrl }: TraderAgentDemoSectionProps) {
  const hasVideo = Boolean(videoUrl);

  return (
    <section style={{ padding: "0 1.5rem 2.25rem" }}>
      <div className="container" style={{ maxWidth: "1120px" }}>
        <div className="feature-grid" style={{ display: "grid", gridTemplateColumns: "1.05fr 0.95fr", gap: "1rem" }}>
          <article
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: "14px",
              padding: "1.4rem",
            }}
          >
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.74rem", color: "var(--muted)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "0.6rem" }}>
              Step 2
            </div>
            <h2 style={{ fontFamily: "var(--font-head)", fontSize: "clamp(1.7rem, 4vw, 2.4rem)", color: "var(--white)", marginBottom: "0.7rem" }}>
              Now watch a high-risk agent workflow.
            </h2>
            <p style={{ color: "var(--silver)", lineHeight: 1.7, marginBottom: "1rem" }}>
              Aletheia Trader is a signal-first paper-trading agent where every
              decision is reviewed, logged, and signed before execution. It
              demonstrates how Aletheia protects workflows where unsafe action
              needs to be stopped and every decision needs evidence.
            </p>
            <div
              style={{
                background: "var(--surface-2)",
                border: "1px solid var(--border-hi)",
                borderRadius: "12px",
                padding: "1rem",
                marginBottom: "0.9rem",
              }}
            >
              <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.74rem", color: "var(--muted)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "0.45rem" }}>
                Required disclaimer
              </div>
              <div style={{ color: "var(--silver)", lineHeight: 1.6 }}>
                Paper-trading demo. Not financial advice. No autonomous live trading.
              </div>
            </div>
            {hasVideo ? (
              <a className="btn-primary" href={videoUrl} target="_blank" rel="noopener noreferrer">
                Watch Trader Agent Demo
              </a>
            ) : (
              <div>
                <div style={{ color: "var(--muted)", marginBottom: "0.8rem" }}>
                  Demo video coming soon.
                </div>
                <a className="btn-primary" href="/demo">
                  Watch Trader Agent Demo
                </a>
              </div>
            )}
          </article>

          <div
            style={{
              border: "1px solid var(--border-hi)",
              borderRadius: "14px",
              background:
                "linear-gradient(160deg, rgba(14,17,21,1), rgba(27,33,44,1))",
              padding: "1.4rem",
              display: "grid",
              alignItems: "end",
            }}
          >
            <div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.74rem", color: "var(--silver)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "0.5rem" }}>
                Trader Agent Demo
              </div>
              <div style={{ fontFamily: "var(--font-head)", fontSize: "1.35rem", color: "var(--white)", marginBottom: "0.7rem" }}>
                Evidence before execution.
              </div>
              <p style={{ color: "var(--silver)", lineHeight: 1.7 }}>
                Show how a higher-risk workflow can move from signal to signed verdict
                without granting the agent uncontrolled execution.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
