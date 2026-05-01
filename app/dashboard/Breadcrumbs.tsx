"use client";

import { usePathname } from "next/navigation";

const LABELS: Record<string, string> = {
  dashboard: "Dashboard",
  keys: "API Keys",
  usage: "Usage",
  logs: "Audit Logs",
  policy: "Policy",
  evidence: "Evidence",
  settings: "Settings",
};

export default function Breadcrumbs() {
  const pathname = usePathname();
  const segments = pathname.split("/").filter(Boolean);

  if (segments.length <= 1) return null;

  const crumbs = segments.map((seg, i) => ({
    label: LABELS[seg] || seg.charAt(0).toUpperCase() + seg.slice(1),
    href: "/" + segments.slice(0, i + 1).join("/"),
    isLast: i === segments.length - 1,
  }));

  return (
    <nav
      aria-label="Breadcrumb"
      style={{
        fontFamily: "var(--font-mono)",
        fontSize: "0.72rem",
        color: "var(--muted)",
        marginBottom: "1rem",
        display: "flex",
        alignItems: "center",
        gap: "0.4rem",
        flexWrap: "wrap",
      }}
    >
      {crumbs.map(({ label, href, isLast }) => (
        <span
          key={href}
          style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}
        >
          {isLast ? (
            <span style={{ color: "var(--silver)" }}>{label}</span>
          ) : (
            <>
              <a
                href={href}
                style={{
                  color: "var(--muted)",
                  textDecoration: "none",
                }}
              >
                {label}
              </a>
              <span style={{ color: "var(--border-hi)" }}>/</span>
            </>
          )}
        </span>
      ))}
    </nav>
  );
}
