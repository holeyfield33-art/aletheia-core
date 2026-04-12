"use client";

import { useState } from "react";
import UpgradeButton from "@/app/components/UpgradeButton";

const cardStyle: React.CSSProperties = {
  background: "var(--surface)",
  border: "1px solid var(--border)",
  padding: "1.5rem",
};

function WelcomeBanner({ onDismiss }: { onDismiss: () => void }) {
  return (
    <div
      style={{
        background: "var(--crimson-glow)",
        border: "1px solid var(--crimson)",
        borderRadius: "10px",
        padding: "1.5rem 1.75rem",
        marginBottom: "1.5rem",
        position: "relative",
      }}
    >
      <button
        onClick={onDismiss}
        aria-label="Dismiss welcome banner"
        style={{
          position: "absolute",
          top: "0.75rem",
          right: "0.75rem",
          background: "none",
          border: "none",
          color: "var(--muted)",
          cursor: "pointer",
          fontSize: "1.1rem",
          padding: "0.25rem",
        }}
      >
        ✕
      </button>
      <h2
        style={{
          fontFamily: "var(--font-head)",
          fontSize: "1.15rem",
          fontWeight: 800,
          color: "var(--white)",
          marginBottom: "0.5rem",
        }}
      >
        Welcome to Aletheia Core
      </h2>
      <p
        style={{
          color: "var(--silver)",
          fontSize: "0.9rem",
          lineHeight: 1.6,
          marginBottom: "1rem",
          maxWidth: "560px",
        }}
      >
        Get started in 3 steps: generate an API key, send your first audit request, and review the signed receipt.
      </p>
      <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
        {[
          { step: "1", label: "Generate API Key", href: "/dashboard/keys" },
          { step: "2", label: "Try Live Demo", href: "/demo" },
          { step: "3", label: "View Audit Logs", href: "/dashboard/logs" },
        ].map(({ step, label, href }) => (
          <a
            key={step}
            href={href}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              background: "var(--surface)",
              border: "1px solid var(--border-hi)",
              borderRadius: "6px",
              padding: "0.5rem 1rem",
              textDecoration: "none",
              transition: "border-color 0.15s",
            }}
          >
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "0.75rem",
                fontWeight: 700,
                color: "var(--crimson-hi)",
                background: "var(--crimson-glow)",
                width: "22px",
                height: "22px",
                borderRadius: "50%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              {step}
            </span>
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "0.82rem",
                color: "var(--silver)",
              }}
            >
              {label}
            </span>
          </a>
        ))}
      </div>
    </div>
  );
}

export default function DashboardOverview({
  keyCount,
  totalRequests,
  logCount,
  plan,
  isNewUser,
  totalQuota,
}: {
  keyCount: number;
  totalRequests: number;
  logCount: number;
  plan: string;
  isNewUser: boolean;
  totalQuota: number;
}) {
  const [showWelcome, setShowWelcome] = useState(isNewUser);

  const usagePct = totalQuota > 0 ? Math.round((totalRequests / totalQuota) * 100) : 0;
  const showUpgradeBanner = plan === "TRIAL" && usagePct >= 80 && !isNewUser;

  const cards = [
    { label: "Active API Keys", value: keyCount, href: "/dashboard/keys" },
    { label: "Total Requests", value: totalRequests.toLocaleString(), href: "/dashboard/usage" },
    { label: "Audit Decisions", value: logCount.toLocaleString(), href: "/dashboard/logs" },
    { label: "Plan", value: plan, href: "/dashboard/usage" },
  ];

  return (
    <div>
      {showWelcome && <WelcomeBanner onDismiss={() => setShowWelcome(false)} />}
      {showUpgradeBanner && (
        <div
          style={{
            background: "rgba(230, 126, 34, 0.08)",
            border: "1px solid #e67e22",
            borderRadius: "10px",
            padding: "1.25rem 1.5rem",
            marginBottom: "1.5rem",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "1rem",
            flexWrap: "wrap",
          }}
        >
          <div>
            <div
              style={{
                fontFamily: "var(--font-head)",
                fontSize: "0.95rem",
                fontWeight: 700,
                color: "var(--white)",
                marginBottom: "0.25rem",
              }}
            >
              {usagePct >= 100 ? "Quota exceeded" : `${usagePct}% of your monthly quota used`}
            </div>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "0.78rem",
                color: "var(--silver)",
              }}
            >
              {totalRequests.toLocaleString()} / {totalQuota.toLocaleString()} requests &middot; Upgrade to Pro for 100K/month
            </div>
          </div>
          <UpgradeButton
            label="Upgrade to Pro"
            style={{ fontSize: "0.82rem", padding: "0.5rem 1.25rem", flexShrink: 0 }}
          />
        </div>
      )}
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
