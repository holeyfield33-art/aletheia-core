"use client";

import { useState } from "react";
import { signOut } from "next-auth/react";
import UpgradeButton from "@/app/components/UpgradeButton";

export default function SettingsClient({
  name,
  email,
  plan,
  createdAt,
}: {
  name: string | null;
  email: string | null;
  plan: string;
  createdAt: string;
}) {
  const [displayName, setDisplayName] = useState(name || "");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  async function handleSaveName(e: React.FormEvent) {
    e.preventDefault();
    if (saving) return;
    setSaving(true);
    setSaved(false);
    try {
      const res = await fetch("/api/settings", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: displayName.trim() }),
      });
      if (res.ok) setSaved(true);
    } catch {
      // Silently fail
    } finally {
      setSaving(false);
    }
  }

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
        Settings
      </div>
      <h1
        style={{
          fontFamily: "var(--font-head)",
          fontSize: "1.5rem",
          fontWeight: 800,
          color: "var(--white)",
          marginBottom: "2rem",
        }}
      >
        Account Settings
      </h1>

      {/* Profile */}
      <section
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "8px",
          padding: "1.5rem",
          marginBottom: "1.5rem",
        }}
      >
        <h2
          style={{
            fontFamily: "var(--font-head)",
            fontSize: "1rem",
            fontWeight: 700,
            color: "var(--white)",
            marginBottom: "1rem",
          }}
        >
          Profile
        </h2>
        <form onSubmit={handleSaveName}>
          <div style={{ marginBottom: "1rem" }}>
            <label htmlFor="settings-name">Display Name</label>
            <input
              id="settings-name"
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              maxLength={100}
              style={{ maxWidth: "400px" }}
            />
          </div>
          <div style={{ marginBottom: "1rem" }}>
            <label>Email</label>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "0.85rem",
                color: "var(--silver)",
                padding: "0.5rem 0",
              }}
            >
              {email || "—"}
            </div>
          </div>
          <div style={{ marginBottom: "1rem" }}>
            <label>Member Since</label>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "0.85rem",
                color: "var(--silver)",
                padding: "0.5rem 0",
              }}
            >
              {createdAt}
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <button
              type="submit"
              disabled={saving}
              className="btn-primary"
              style={{
                fontSize: "0.85rem",
                padding: "0.5rem 1.25rem",
                opacity: saving ? 0.7 : 1,
                cursor: saving ? "not-allowed" : "pointer",
              }}
            >
              {saving ? "Saving…" : "Save Changes"}
            </button>
            {saved && (
              <span
                style={{
                  color: "var(--green)",
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.78rem",
                }}
              >
                ✓ Saved
              </span>
            )}
          </div>
        </form>
      </section>

      {/* Plan */}
      <section
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "8px",
          padding: "1.5rem",
          marginBottom: "1.5rem",
        }}
      >
        <h2
          style={{
            fontFamily: "var(--font-head)",
            fontSize: "1rem",
            fontWeight: 700,
            color: "var(--white)",
            marginBottom: "1rem",
          }}
        >
          Plan & Billing
        </h2>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "1rem",
            marginBottom: "1rem",
            flexWrap: "wrap",
          }}
        >
          <span
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "0.85rem",
              color: "var(--white)",
              background: plan === "PRO" ? "var(--crimson-glow)" : "var(--surface-2)",
              border: `1px solid ${plan === "PRO" ? "var(--crimson)" : "var(--border-hi)"}`,
              padding: "0.35rem 0.85rem",
              borderRadius: "4px",
            }}
          >
            {plan} Plan
          </span>
          <span
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "0.78rem",
              color: "var(--muted)",
            }}
          >
            {plan === "TRIAL" && "1,000 requests/month · 1 API key"}
            {plan === "PRO" && "100,000 requests/month · 10 API keys"}
            {plan === "ENTERPRISE" && "Custom limits"}
          </span>
        </div>
        {plan === "TRIAL" && (
          <UpgradeButton
            label="Upgrade to Pro — $49/mo"
            style={{ fontSize: "0.85rem", padding: "0.5rem 1.25rem" }}
          />
        )}
      </section>

      {/* Danger zone */}
      <section
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "8px",
          padding: "1.5rem",
        }}
      >
        <h2
          style={{
            fontFamily: "var(--font-head)",
            fontSize: "1rem",
            fontWeight: 700,
            color: "var(--crimson-hi)",
            marginBottom: "1rem",
          }}
        >
          Session
        </h2>
        <button
          onClick={() => signOut({ callbackUrl: "/" })}
          className="btn-secondary"
          style={{
            fontSize: "0.85rem",
            padding: "0.5rem 1.25rem",
            borderColor: "var(--crimson)",
            color: "var(--crimson-hi)",
          }}
        >
          Sign Out
        </button>
      </section>
    </div>
  );
}
