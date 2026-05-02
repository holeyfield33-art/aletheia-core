import Link from "next/link";

type RedTeamDemoSectionProps = {
  videoUrl?: string;
};

export default function RedTeamDemoSection({ videoUrl }: RedTeamDemoSectionProps) {
  const hasVideo = Boolean(videoUrl);

  return (
    <section style={{ padding: "2.25rem 1.5rem" }}>
      <div className="container" style={{ maxWidth: "1120px" }}>
        <div className="feature-grid" style={{ display: "grid", gridTemplateColumns: "0.9fr 1.1fr", gap: "1rem" }}>
          <div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.74rem", color: "var(--muted)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "0.6rem" }}>
              Step 1
            </div>
            <h2 style={{ fontFamily: "var(--font-head)", fontSize: "clamp(1.7rem, 4vw, 2.4rem)", color: "var(--white)", marginBottom: "0.7rem" }}>
              First, watch the attack.
            </h2>
            <p style={{ color: "var(--silver)", lineHeight: 1.7, marginBottom: "0.85rem" }}>
              Prompt injection is not just bad text. Once an AI agent has tools,
              a malicious prompt can become a shell command, config change,
              leaked secret, or unauthorized action.
            </p>
            <p style={{ color: "var(--muted)", lineHeight: 1.7 }}>
              This is the failure mode Aletheia was built to stop.
            </p>
          </div>

          <article
            style={{
              background: "linear-gradient(180deg, rgba(20,24,32,1), rgba(14,17,21,1))",
              border: "1px solid var(--border-hi)",
              borderRadius: "14px",
              padding: "1.4rem",
            }}
          >
            <div
              style={{
                minHeight: "260px",
                borderRadius: "12px",
                border: "1px solid var(--border)",
                background:
                  "linear-gradient(145deg, rgba(176,34,54,0.28), rgba(8,10,12,0.9))",
                padding: "1.4rem",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
              }}
            >
              <div>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.74rem", color: "var(--silver)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "0.5rem" }}>
                  Red Team Demo
                </div>
                <div style={{ fontFamily: "var(--font-head)", fontSize: "1.45rem", color: "var(--white)", marginBottom: "0.7rem" }}>
                  {hasVideo ? "Watch the Attack" : "Demo video coming soon"}
                </div>
                <p style={{ color: "var(--silver)", lineHeight: 1.65 }}>
                  {hasVideo
                    ? "Review a live red-team sequence against a tool-enabled agent workflow."
                    : "Use the live demo today while the dedicated red-team walkthrough is being finalized."}
                </p>
              </div>

              {hasVideo ? (
                <a className="btn-primary" href={videoUrl} target="_blank" rel="noopener noreferrer">
                  Watch the Attack
                </a>
              ) : (
                <Link className="btn-primary" href="/demo">
                  Run Live Demo
                </Link>
              )}
            </div>
          </article>
        </div>
      </div>
    </section>
  );
}
