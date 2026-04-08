import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Dashboard",
  description: "Aletheia Core operational dashboard. Audit logs, policy management, evidence export, and API key administration.",
};

const NAV_ITEMS = [
  { label: "Trial Keys", href: "/dashboard/keys" },
  { label: "Usage", href: "/dashboard/usage" },
  { label: "Audit Logs", href: "/dashboard/logs" },
  { label: "Policy", href: "/dashboard/policy" },
  { label: "Evidence", href: "/dashboard/evidence" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", minHeight: "calc(100vh - 60px)" }}>
      {/* Sidebar */}
      <aside
        style={{
          width: "200px",
          flexShrink: 0,
          background: "#09090b",
          borderRight: "1px solid var(--border)",
          padding: "1.5rem 0",
        }}
      >
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "0.7rem",
            color: "var(--muted)",
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            padding: "0 1.25rem",
            marginBottom: "1rem",
          }}
        >
          Dashboard
        </div>
        <nav style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
          {NAV_ITEMS.map(({ label, href }) => (
            <a
              key={href}
              href={href}
              style={{
                display: "block",
                padding: "0.55rem 1.25rem",
                fontFamily: "var(--font-mono)",
                fontSize: "0.82rem",
                color: "var(--silver)",
                textDecoration: "none",
                borderLeft: "2px solid transparent",
                transition: "background 0.15s, border-color 0.15s",
              }}
            >
              {label}
            </a>
          ))}
        </nav>
      </aside>

      {/* Main content */}
      <div
        style={{
          flex: 1,
          background: "#09090b",
          padding: "2rem 2.5rem",
          overflowX: "auto",
        }}
      >
        {children}
      </div>
    </div>
  );
}
