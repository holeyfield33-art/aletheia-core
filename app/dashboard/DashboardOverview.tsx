"use client";

const cardStyle: React.CSSProperties = {
  background: "var(--surface)",
  border: "1px solid var(--border)",
  padding: "1.5rem",
};

export default function DashboardOverview({
  keyCount,
  totalRequests,
  logCount,
  plan,
}: {
  keyCount: number;
  totalRequests: number;
  logCount: number;
  plan: string;
}) {
  const cards = [
    { label: "Active API Keys", value: keyCount, href: "/dashboard/keys" },
    { label: "Total Requests", value: totalRequests.toLocaleString(), href: "/dashboard/usage" },
    { label: "Audit Decisions", value: logCount.toLocaleString(), href: "/dashboard/logs" },
    { label: "Plan", value: plan, href: "/dashboard/usage" },
  ];

  return (
    <div>
      <div
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "0.7rem",
          color: "var(--muted)",
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          marginBottom: "0.75rem",
        }}
      >
        Overview
      </div>
      <h1
        style={{
          fontFamily: "var(--font-head)",
          fontSize: "1.5rem",
          fontWeight: 800,
          color: "var(--white)",
          marginBottom: "1.5rem",
        }}
      >
        Dashboard
      </h1>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: "1rem",
          marginBottom: "2rem",
        }}
      >
        {cards.map(({ label, value, href }) => (
          <a key={label} href={href} style={{ ...cardStyle, textDecoration: "none" }}>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "0.7rem",
                color: "var(--muted)",
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                marginBottom: "0.5rem",
              }}
            >
              {label}
            </div>
            <div
              style={{
                fontFamily: "var(--font-head)",
                fontSize: "1.75rem",
                fontWeight: 800,
                color: "var(--white)",
              }}
            >
              {value}
            </div>
          </a>
        ))}
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
          gap: "1rem",
        }}
      >
        {[
          { label: "API Keys", href: "/dashboard/keys", desc: "Generate, view, and revoke your API keys" },
          { label: "Usage & Quota", href: "/dashboard/usage", desc: "Monitor request usage per key" },
          { label: "Audit Logs", href: "/dashboard/logs", desc: "View decision history and threat analysis" },
          { label: "Policy", href: "/dashboard/policy", desc: "View security policy configuration" },
          { label: "Evidence Export", href: "/dashboard/evidence", desc: "Export signed audit evidence (JSONL)" },
        ].map(({ label, href, desc }) => (
          <a
            key={href}
            href={href}
            style={{
              display: "block",
              ...cardStyle,
              textDecoration: "none",
              transition: "border-color 0.15s",
            }}
          >
            <div
              style={{
                fontFamily: "var(--font-head)",
                fontSize: "1rem",
                fontWeight: 700,
                color: "var(--white)",
                marginBottom: "0.4rem",
              }}
            >
              {label}
            </div>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "0.78rem",
                color: "var(--muted)",
                lineHeight: 1.5,
              }}
            >
              {desc}
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
