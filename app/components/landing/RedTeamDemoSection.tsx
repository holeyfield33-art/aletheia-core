import AttackTeaserPanel from "@/app/components/landing/AttackTeaserPanel";

export default function RedTeamDemoSection() {

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

          <AttackTeaserPanel />
        </div>
      </div>
    </section>
  );
}
