"use client";

import { usePathname } from "next/navigation";
import { signOut } from "next-auth/react";

const NAV_ITEMS = [
  { label: "Overview", href: "/dashboard" },
  { label: "API Keys", href: "/dashboard/keys" },
  { label: "Usage", href: "/dashboard/usage" },
  { label: "Audit Logs", href: "/dashboard/logs" },
  { label: "Policy", href: "/dashboard/policy" },
  { label: "Evidence", href: "/dashboard/evidence" },
];

export default function DashboardSidebar({
  userName,
  userPlan,
}: {
  userName?: string | null;
  userPlan?: string;
}) {
  const pathname = usePathname();

  return (
    <aside
      style={{
        width: "200px",
        flexShrink: 0,
        background: "#09090b",
        borderRight: "1px solid var(--border)",
        padding: "1.5rem 0",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
      }}
    >
      <div>
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
          {NAV_ITEMS.map(({ label, href }) => {
            const active =
              href === "/dashboard"
                ? pathname === "/dashboard"
                : pathname.startsWith(href);
            return (
              <a
                key={href}
                href={href}
                style={{
                  display: "block",
                  padding: "0.55rem 1.25rem",
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.82rem",
                  color: active ? "var(--white)" : "var(--silver)",
                  textDecoration: "none",
                  borderLeft: active
                    ? "2px solid var(--crimson)"
                    : "2px solid transparent",
                  background: active ? "rgba(220,38,38,0.06)" : "transparent",
                  transition: "background 0.15s, border-color 0.15s",
                }}
              >
                {label}
              </a>
            );
          })}
        </nav>
      </div>

      {/* User info + sign out */}
      <div style={{ padding: "1rem 1.25rem", borderTop: "1px solid var(--border)" }}>
        {userName && (
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "0.75rem",
              color: "var(--silver)",
              marginBottom: "0.25rem",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {userName}
          </div>
        )}
        {userPlan && (
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "0.65rem",
              color: "var(--muted)",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              marginBottom: "0.75rem",
            }}
          >
            {userPlan} plan
          </div>
        )}
        <button
          onClick={() => signOut({ callbackUrl: "/" })}
          style={{
            width: "100%",
            padding: "0.45rem",
            background: "transparent",
            border: "1px solid var(--border)",
            color: "var(--muted)",
            fontFamily: "var(--font-mono)",
            fontSize: "0.72rem",
            cursor: "pointer",
            transition: "color 0.15s",
          }}
        >
          Sign Out
        </button>
      </div>
    </aside>
  );
}
