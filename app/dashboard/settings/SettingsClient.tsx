"use client";

import { useState } from "react";
import { signOut } from "next-auth/react";
import UpgradeButton from "@/app/components/UpgradeButton";
import { useToast } from "@/app/components/Toast";

export default function SettingsClient({
  name,
  email,
  plan,
  createdAt,
  hasPassword,
}: {
  name: string | null;
  email: string | null;
  plan: string;
  createdAt: string;
  hasPassword: boolean;
}) {
  const [displayName, setDisplayName] = useState(name || "");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");
  const [deleteEmailConfirm, setDeleteEmailConfirm] = useState("");
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const toast = useToast();
  const normalizedEmail = email?.toLowerCase() ?? "";

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
      if (res.ok) {
        setSaved(true);
        toast.success("Settings saved");
      } else {
        toast.error("Failed to save settings");
      }
    } catch {
      toast.error("Failed to save settings");
    } finally {
      setSaving(false);
    }
  }

  async function handleExport() {
    if (exporting) return;
    setExporting(true);
    try {
      const res = await fetch("/api/account/export", { method: "POST" });
      if (!res.ok) {
        const data = await res.json();
        toast.error(data.message || "Export failed.");
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `aletheia-data-export-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success("Data exported");
    } catch {
      toast.error("Export failed. Please try again.");
    } finally {
      setExporting(false);
    }
  }

  async function handleDeleteAccount() {
    if (deleting) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      const res = await fetch("/api/account", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: deletePassword, confirmEmail: deleteEmailConfirm }),
      });
      const data = await res.json();
      if (!res.ok) {
        setDeleteError(data.message || "Deletion failed.");
        setDeleting(false);
        return;
      }
      signOut({ callbackUrl: "/" });
    } catch {
      setDeleteError("An unexpected error occurred.");
      setDeleting(false);
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
              background: plan === "TRIAL" ? "var(--surface-2)" : "var(--crimson-glow)",
              border: `1px solid ${plan === "TRIAL" ? "var(--border-hi)" : "var(--crimson)"}`,
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
            {plan === "PRO" && "50,000 requests/month · 10 API keys"}
            {plan === "MAX" && "200,000 requests/month · 10 API keys"}
            {plan === "ENTERPRISE" && "Custom limits"}
          </span>
        </div>
        {plan === "TRIAL" && (
          <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
            <UpgradeButton
              label="Upgrade to Pro — $29.99/mo"
              plan="PRO"
              style={{ fontSize: "0.85rem", padding: "0.5rem 1.25rem" }}
            />
            <UpgradeButton
              label="Upgrade to Max — $49.99/mo"
              plan="MAX"
              className="btn-secondary"
              style={{ fontSize: "0.85rem", padding: "0.5rem 1.25rem" }}
            />
          </div>
        )}
      </section>

      {/* Danger zone */}
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

      {/* Your Data (CCPA/CPRA) */}
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
            marginBottom: "0.5rem",
          }}
        >
          Your Data
        </h2>
        <p
          style={{
            fontSize: "0.82rem",
            color: "var(--muted)",
            marginBottom: "1rem",
            lineHeight: 1.6,
          }}
        >
          Export a copy of your profile, API keys metadata, and audit logs (90 days). You can also
          permanently delete your account and all associated data.
        </p>
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <button
            onClick={handleExport}
            disabled={exporting}
            className="btn-secondary"
            style={{
              fontSize: "0.85rem",
              padding: "0.5rem 1.25rem",
              opacity: exporting ? 0.7 : 1,
              cursor: exporting ? "not-allowed" : "pointer",
            }}
          >
            {exporting ? "Exporting…" : "Export My Data"}
          </button>
          <button
            onClick={() => setDeleteConfirmOpen(!deleteConfirmOpen)}
            className="btn-secondary"
            style={{
              fontSize: "0.85rem",
              padding: "0.5rem 1.25rem",
              borderColor: "var(--crimson)",
              color: "var(--crimson-hi)",
            }}
          >
            Delete My Account
          </button>
        </div>
        {deleteConfirmOpen && (
          <div
            style={{
              marginTop: "1rem",
              padding: "1rem",
              background: "rgba(220,38,38,0.08)",
              border: "1px solid rgba(220,38,38,0.25)",
              borderRadius: "6px",
            }}
          >
            <p
              style={{
                fontSize: "0.82rem",
                color: "#f87171",
                marginBottom: "0.75rem",
                lineHeight: 1.6,
              }}
            >
              This will permanently delete your account after a 30-day grace period. All API keys will
              be revoked immediately. This action cannot be undone.
            </p>
            {hasPassword && (
              <input
                type="password"
                placeholder="Confirm your password"
                value={deletePassword}
                onChange={(e) => setDeletePassword(e.target.value)}
                style={{
                  width: "100%",
                  maxWidth: "300px",
                  padding: "0.5rem 0.75rem",
                  background: "#09090b",
                  border: "1px solid var(--border)",
                  color: "var(--white)",
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.85rem",
                  marginBottom: "0.75rem",
                  boxSizing: "border-box",
                }}
              />
            )}
            {!hasPassword && (
              <input
                type="email"
                placeholder="Type your email to confirm deletion"
                value={deleteEmailConfirm}
                onChange={(e) => setDeleteEmailConfirm(e.target.value)}
                style={{
                  width: "100%",
                  maxWidth: "300px",
                  padding: "0.5rem 0.75rem",
                  background: "#09090b",
                  border: "1px solid var(--border)",
                  color: "var(--white)",
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.85rem",
                  marginBottom: "0.75rem",
                  boxSizing: "border-box",
                }}
              />
            )}
            {deleteError && (
              <p style={{ color: "#f87171", fontSize: "0.8rem", marginBottom: "0.5rem" }}>
                {deleteError}
              </p>
            )}
            <button
              onClick={handleDeleteAccount}
              disabled={
                deleting ||
                (hasPassword && !deletePassword) ||
                (!hasPassword && deleteEmailConfirm.trim().toLowerCase() !== normalizedEmail)
              }
              style={{
                fontSize: "0.82rem",
                padding: "0.45rem 1rem",
                background: "var(--crimson)",
                color: "var(--white)",
                border: "none",
                cursor: deleting ? "not-allowed" : "pointer",
                opacity:
                  deleting ||
                  (hasPassword && !deletePassword) ||
                  (!hasPassword && deleteEmailConfirm.trim().toLowerCase() !== normalizedEmail)
                    ? 0.5
                    : 1,
              }}
            >
              {deleting ? "Deleting…" : "Permanently Delete Account"}
            </button>
          </div>
        )}
      </section>

      {/* Legal */}
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
            color: "var(--white)",
            marginBottom: "0.75rem",
          }}
        >
          Legal
        </h2>
        <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
          {[
            { label: "Privacy Policy", href: "/legal/privacy" },
            { label: "Terms of Service", href: "/legal/terms" },
            { label: "Acceptable Use Policy", href: "/legal/acceptable-use" },
            { label: "Subscription & Billing Terms", href: "/legal/billing" },
            { label: "Cookie & Tracking Disclosure", href: "/legal/cookies" },
            { label: "Accessibility", href: "/legal/accessibility" },
            { label: "Security & Trust", href: "/legal/security" },
          ].map(({ label, href }) => (
            <a
              key={href}
              href={href}
              style={{
                color: "var(--crimson-hi)",
                fontSize: "0.85rem",
                textDecoration: "none",
              }}
            >
              {label}
            </a>
          ))}
        </div>
      </section>
    </div>
  );
}
