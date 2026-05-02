import { getRecommendedAction } from "@/lib/onboarding";

type WelcomeActionCardsProps = {
  useCase?: string | null;
  primaryGoal?: string | null;
  agentType?: string | null;
  onboardingCompleted?: boolean;
};

const cardStyle: React.CSSProperties = {
  background: "var(--surface)",
  border: "1px solid var(--border)",
  borderRadius: "12px",
  padding: "1.1rem",
  textDecoration: "none",
};

export default function WelcomeActionCards({
  useCase,
  primaryGoal,
  agentType,
  onboardingCompleted,
}: WelcomeActionCardsProps) {
  const recommended = getRecommendedAction(primaryGoal, useCase, agentType);

  return (
    <section
      style={{
        background: "linear-gradient(180deg, var(--surface), var(--surface-2))",
        border: "1px solid var(--border-hi)",
        borderRadius: "14px",
        padding: "1.5rem",
        marginBottom: "1.5rem",
      }}
    >
      <div style={{ marginBottom: "1rem" }}>
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "0.72rem",
            color: "var(--muted)",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            marginBottom: "0.5rem",
          }}
        >
          Welcome
        </div>
        <h2 style={{ fontFamily: "var(--font-head)", fontSize: "1.5rem", color: "var(--white)", marginBottom: "0.35rem" }}>
          Welcome to Aletheia Core
        </h2>
        <p style={{ color: "var(--silver)", lineHeight: 1.65 }}>
          Your runtime firewall is ready to test.
        </p>
      </div>

      <div className="feature-grid" style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: "1rem", marginBottom: "1rem" }}>
        {[
          {
            label: "Run Live Attack Demo",
            href: "/demo",
            desc: "Launch attack scenarios and inspect the signed result.",
          },
          {
            label: "Verify a Receipt",
            href: "/verify",
            desc: "Check receipt structure and hash consistency before sharing evidence.",
          },
          {
            label: "Get API Key / Connect Agent",
            href: "/dashboard/keys",
            desc: "Use the existing key management flow to connect your agent.",
          },
        ].map((card) => (
          <a key={card.label} href={card.href} style={cardStyle}>
            <div style={{ fontFamily: "var(--font-head)", fontSize: "1.05rem", color: "var(--white)", marginBottom: "0.4rem" }}>
              {card.label}
            </div>
            <div style={{ color: "var(--muted)", fontSize: "0.84rem", lineHeight: 1.55 }}>
              {card.desc}
            </div>
          </a>
        ))}
      </div>

      <div className="feature-grid" style={{ display: "grid", gridTemplateColumns: "1.2fr 0.8fr", gap: "1rem" }}>
        <div style={{ ...cardStyle, background: "var(--surface-2)" }}>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", color: "var(--muted)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "0.5rem" }}>
            Profile Summary
          </div>
          <div style={{ display: "grid", gap: "0.45rem", color: "var(--silver)" }}>
            <div>Use case: {useCase ?? "Not set"}</div>
            <div>Primary risk: {primaryGoal ?? "Not set"}</div>
            <div>Tool access profile: {agentType ?? "Not set"}</div>
            <div>Onboarding completed: {onboardingCompleted ? "Yes" : "No"}</div>
          </div>
        </div>

        <div style={{ ...cardStyle, background: "var(--crimson-glow)", border: "1px solid var(--crimson)" }}>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", color: "var(--silver)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "0.5rem" }}>
            Recommended
          </div>
          <div style={{ fontFamily: "var(--font-head)", color: "var(--white)", fontSize: "1.15rem", marginBottom: "0.6rem" }}>
            {recommended.label}
          </div>
          <a className="btn-primary" href={recommended.href}>
            {recommended.label}
          </a>
        </div>
      </div>
    </section>
  );
}
