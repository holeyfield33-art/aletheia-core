import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Dashboard",
};

export default function DashboardIndex() {
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
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "1rem",
          marginBottom: "2rem",
        }}
      >
        {[
          { label: "Audit Logs", href: "/dashboard/logs", desc: "View audit logs and decision receipts" },
          { label: "Policy", href: "/dashboard/policy", desc: "View and manage security_policy.json" },
          { label: "Evidence", href: "/dashboard/evidence", desc: "Export signed audit evidence (JSONL)" },
          { label: "Trial API Keys", href: "/dashboard/keys", desc: "Generate, view, and revoke trial API keys" },
        ].map(({ label, href, desc }) => (
          <a
            key={href}
            href={href}
            style={{
              display: "block",
              background: "var(--surface)",
              border: "1px solid var(--border)",
              padding: "1.25rem",
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
