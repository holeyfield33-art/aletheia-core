import Link from "next/link";
import VideoWithPlayButton from "@/app/components/landing/VideoWithPlayButton";

type TraderAgentDemoSectionProps = {
  videoUrl?: string;
  thumbnailUrl?: string;
};

export default function TraderAgentDemoSection({ videoUrl, thumbnailUrl }: TraderAgentDemoSectionProps) {
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
            {videoUrl ? (
              <a className="btn-primary" href="#trader-demo-video">
                Watch Looping Demo ↓
              </a>
            ) : (
              <Link className="btn-primary" href="/demo">
                Interactive Trader Demo →
              </Link>
            )}
          </article>

          <VideoWithPlayButton
            title="Trader Agent Demo"
            description="Signal → Verdict → Receipt. Evidence before execution."
            videoUrl={videoUrl}
            thumbnailUrl={thumbnailUrl}
            fallbackText="Video coming soon. Try interactive demo instead →"
            containerId="trader-demo-video"
          />
        </div>
      </div>
    </section>
  );
}
