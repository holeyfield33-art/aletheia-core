"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

type OnboardingProfile = {
  fullName?: string | null;
  companyName?: string | null;
  role?: string | null;
  useCase?: string | null;
  agentType?: string | null;
  handlesSensitiveData?: boolean;
  primaryGoal?: string | null;
};

type OnboardingWizardProps = {
  useCaseOptions: readonly string[];
  toolOptions: readonly string[];
  riskOptions: readonly string[];
  initialProfile: OnboardingProfile | null;
  initialFullName?: string | null;
};

function parseInitialTools(value: string | null | undefined): string[] {
  if (!value) return [];
  return value
    .split(",")
    .map((entry) => entry.trim())
    .filter(Boolean);
}

export default function OnboardingWizard({
  useCaseOptions,
  toolOptions,
  riskOptions,
  initialProfile,
  initialFullName,
}: OnboardingWizardProps) {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [fullName, setFullName] = useState(
    initialProfile?.fullName ?? initialFullName ?? "",
  );
  const [companyName, setCompanyName] = useState(initialProfile?.companyName ?? "");
  const [role, setRole] = useState(initialProfile?.role ?? "");
  const [useCase, setUseCase] = useState(initialProfile?.useCase ?? "");
  const [agentTypes, setAgentTypes] = useState<string[]>(
    parseInitialTools(initialProfile?.agentType),
  );
  const [handlesSensitiveData, setHandlesSensitiveData] = useState(
    initialProfile?.handlesSensitiveData ?? false,
  );
  const [primaryGoal, setPrimaryGoal] = useState(initialProfile?.primaryGoal ?? "");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const recommendation = useMemo(() => {
    if (primaryGoal === "I just want to test the demo") {
      return { label: "Run Live Demo", href: "/demo" };
    }
    if (primaryGoal === "Compliance / audit trail") {
      return { label: "Verify Receipt", href: "/verify" };
    }
    if (
      [
        "Prompt injection",
        "Secret leakage",
        "Unsafe shell execution",
        "MCP config tampering",
      ].includes(primaryGoal)
    ) {
      return { label: "Run Attack Scenario", href: "/demo" };
    }
    if (
      useCase === "Trading / finance workflow" ||
      agentTypes.includes("Handles payments or financial actions")
    ) {
      return { label: "Review Runtime Firewall", href: "/ai-agent-security" };
    }
    return { label: "Protect My Agent", href: "/dashboard" };
  }, [agentTypes, primaryGoal, useCase]);

  function toggleAgentType(value: string) {
    setAgentTypes((current) => {
      if (current.includes(value)) {
        return current.filter((entry) => entry !== value);
      }
      if (value === "No tools yet") {
        return [value];
      }
      return current.filter((entry) => entry !== "No tools yet").concat(value);
    });
  }

  async function handleSubmit() {
    if (!useCase || agentTypes.length === 0 || !primaryGoal) {
      setError("Complete all onboarding steps before continuing.");
      return;
    }

    setSubmitting(true);
    setError(null);

    const response = await fetch("/api/onboarding", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        fullName,
        companyName,
        role,
        useCase,
        agentTypes,
        handlesSensitiveData,
        primaryGoal,
      }),
    });

    const payload = await response.json().catch(() => null);
    if (!response.ok) {
      setError(payload?.error ?? "Could not save onboarding.");
      setSubmitting(false);
      return;
    }

    router.push("/dashboard");
    router.refresh();
  }

  const canContinue =
    (step === 0 && Boolean(useCase)) ||
    (step === 1 && agentTypes.length > 0) ||
    (step === 2 && Boolean(primaryGoal)) ||
    step === 3;

  return (
    <div
      style={{
        maxWidth: "900px",
        margin: "0 auto",
        padding: "3.5rem 1.5rem 5rem",
      }}
    >
      <div style={{ marginBottom: "2rem" }}>
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "0.72rem",
            color: "var(--muted)",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            marginBottom: "0.6rem",
          }}
        >
          Onboarding
        </div>
        <h1
          style={{
            fontFamily: "var(--font-head)",
            fontSize: "clamp(1.8rem, 4vw, 2.5rem)",
            fontWeight: 800,
            color: "var(--white)",
            marginBottom: "0.75rem",
          }}
        >
          Configure your runtime firewall path.
        </h1>
        <p style={{ color: "var(--silver)", lineHeight: 1.65, maxWidth: "720px" }}>
          This lightweight setup personalizes the dashboard and takes you to the
          next safest action without changing your auth provider or billing.
        </p>
      </div>

      <div
        style={{
          display: "grid",
          gap: "1rem",
          gridTemplateColumns: "minmax(0, 0.78fr) minmax(280px, 0.22fr)",
        }}
      >
        <section
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "12px",
            padding: "1.5rem",
          }}
        >
          {step === 0 && (
            <div>
              <h2 style={{ fontFamily: "var(--font-head)", fontSize: "1.4rem", marginBottom: "0.5rem" }}>
                What are you protecting?
              </h2>
              <p style={{ color: "var(--silver)", marginBottom: "1rem" }}>
                Choose the workflow that best matches the system you want to protect.
              </p>
              <div className="feature-grid" style={{ display: "grid", gap: "0.75rem", gridTemplateColumns: "repeat(2, minmax(0, 1fr))" }}>
                {useCaseOptions.map((option) => (
                  <button
                    key={option}
                    type="button"
                    onClick={() => setUseCase(option)}
                    style={{
                      textAlign: "left",
                      padding: "1rem",
                      borderRadius: "10px",
                      border:
                        useCase === option
                          ? "1px solid var(--crimson)"
                          : "1px solid var(--border-hi)",
                      background:
                        useCase === option ? "var(--crimson-glow)" : "var(--surface-2)",
                      color: "var(--white)",
                      cursor: "pointer",
                    }}
                  >
                    {option}
                  </button>
                ))}
              </div>
            </div>
          )}

          {step === 1 && (
            <div>
              <h2 style={{ fontFamily: "var(--font-head)", fontSize: "1.4rem", marginBottom: "0.5rem" }}>
                Does your agent use tools?
              </h2>
              <p style={{ color: "var(--silver)", marginBottom: "1rem" }}>
                Select all that apply. If you are early, pick “No tools yet” or “Not sure.”
              </p>
              <div className="feature-grid" style={{ display: "grid", gap: "0.75rem", gridTemplateColumns: "repeat(2, minmax(0, 1fr))" }}>
                {toolOptions.map((option) => {
                  const selected = agentTypes.includes(option);
                  return (
                    <button
                      key={option}
                      type="button"
                      onClick={() => toggleAgentType(option)}
                      style={{
                        textAlign: "left",
                        padding: "1rem",
                        borderRadius: "10px",
                        border: selected
                          ? "1px solid var(--crimson)"
                          : "1px solid var(--border-hi)",
                        background: selected ? "var(--crimson-glow)" : "var(--surface-2)",
                        color: "var(--white)",
                        cursor: "pointer",
                      }}
                    >
                      {option}
                    </button>
                  );
                })}
              </div>

              <div style={{ marginTop: "1rem", display: "grid", gap: "1rem" }}>
                <label style={{ display: "grid", gap: "0.4rem" }}>
                  <span>Full name</span>
                  <input value={fullName} onChange={(e) => setFullName(e.target.value)} maxLength={80} />
                </label>
                <label style={{ display: "grid", gap: "0.4rem" }}>
                  <span>Company name</span>
                  <input value={companyName} onChange={(e) => setCompanyName(e.target.value)} maxLength={120} />
                </label>
                <label style={{ display: "grid", gap: "0.4rem" }}>
                  <span>Role</span>
                  <input value={role} onChange={(e) => setRole(e.target.value)} maxLength={80} />
                </label>
                <label
                  style={{
                    display: "flex",
                    gap: "0.7rem",
                    alignItems: "flex-start",
                    color: "var(--silver)",
                    fontSize: "0.9rem",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={handlesSensitiveData}
                    onChange={(e) => setHandlesSensitiveData(e.target.checked)}
                    style={{ marginTop: "0.2rem", accentColor: "var(--crimson)" }}
                  />
                  <span>Handles sensitive data, secrets, or production records</span>
                </label>
              </div>
            </div>
          )}

          {step === 2 && (
            <div>
              <h2 style={{ fontFamily: "var(--font-head)", fontSize: "1.4rem", marginBottom: "0.5rem" }}>
                What is your biggest risk?
              </h2>
              <p style={{ color: "var(--silver)", marginBottom: "1rem" }}>
                We use this to prioritize the next action in your dashboard.
              </p>
              <div className="feature-grid" style={{ display: "grid", gap: "0.75rem", gridTemplateColumns: "repeat(2, minmax(0, 1fr))" }}>
                {riskOptions.map((option) => (
                  <button
                    key={option}
                    type="button"
                    onClick={() => setPrimaryGoal(option)}
                    style={{
                      textAlign: "left",
                      padding: "1rem",
                      borderRadius: "10px",
                      border:
                        primaryGoal === option
                          ? "1px solid var(--crimson)"
                          : "1px solid var(--border-hi)",
                      background:
                        primaryGoal === option
                          ? "var(--crimson-glow)"
                          : "var(--surface-2)",
                      color: "var(--white)",
                      cursor: "pointer",
                    }}
                  >
                    {option}
                  </button>
                ))}
              </div>
            </div>
          )}

          {step === 3 && (
            <div>
              <h2 style={{ fontFamily: "var(--font-head)", fontSize: "1.4rem", marginBottom: "0.5rem" }}>
                You&apos;re ready.
              </h2>
              <p style={{ color: "var(--silver)", marginBottom: "1rem" }}>
                Your recommended next action is based on the risk path you selected.
              </p>
              <div
                style={{
                  border: "1px solid var(--crimson)",
                  background: "var(--crimson-glow)",
                  borderRadius: "12px",
                  padding: "1.25rem",
                  marginBottom: "1rem",
                }}
              >
                <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.74rem", color: "var(--silver)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "0.4rem" }}>
                  Recommended next action
                </div>
                <a href={recommendation.href} className="btn-primary">
                  {recommendation.label}
                </a>
              </div>

              <div style={{ display: "grid", gap: "0.75rem" }}>
                <div style={{ color: "var(--silver)" }}>Use case: {useCase}</div>
                <div style={{ color: "var(--silver)" }}>
                  Tool access profile: {agentTypes.join(", ")}
                </div>
                <div style={{ color: "var(--silver)" }}>Primary risk: {primaryGoal}</div>
              </div>
            </div>
          )}

          {error && (
            <div
              role="alert"
              style={{
                marginTop: "1rem",
                background: "rgba(176,34,54,0.14)",
                border: "1px solid var(--crimson)",
                color: "var(--silver)",
                borderRadius: "8px",
                padding: "0.85rem 1rem",
              }}
            >
              {error}
            </div>
          )}

          <div style={{ display: "flex", gap: "0.75rem", marginTop: "1.5rem", flexWrap: "wrap" }}>
            {step > 0 && (
              <button type="button" className="btn-secondary" onClick={() => setStep((current) => current - 1)}>
                Back
              </button>
            )}

            {step < 3 ? (
              <button
                type="button"
                className="btn-primary"
                onClick={() => setStep((current) => current + 1)}
                disabled={!canContinue}
                style={{ opacity: canContinue ? 1 : 0.65 }}
              >
                Continue
              </button>
            ) : (
              <>
                <button type="button" className="btn-primary" onClick={handleSubmit} disabled={submitting}>
                  Enter Dashboard
                </button>
                <a className="btn-secondary" href="/demo">
                  Run Live Demo
                </a>
              </>
            )}
          </div>
        </section>

        <aside
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "12px",
            padding: "1.25rem",
            height: "fit-content",
          }}
        >
          <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", color: "var(--muted)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "0.75rem" }}>
            Flow
          </div>
          <div style={{ color: "var(--silver)", lineHeight: 1.7 }}>
            Watch the attack. Watch the agent. Watch Aletheia stop it. Verify the receipt. Protect your own system.
          </div>
        </aside>
      </div>
    </div>
  );
}
