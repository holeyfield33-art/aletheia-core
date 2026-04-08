"use client";

import { useState, useEffect } from "react";
import { CTAS } from "@/lib/site-config";

/* ------------------------------------------------------------------ */
/* Types                                                              */
/* ------------------------------------------------------------------ */

interface KeyUsage {
  id: string;
  name: string;
  key_prefix: string;
  plan: string;
  status: string;
  monthly_quota: number;
  requests_used: number;
  period_start: string;
  period_end: string;
  created_at: string;
  last_used_at: string | null;
}

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function UsagePage() {
  const [keys, setKeys] = useState<KeyUsage[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch("/api/keys");
        if (res.ok) {
          const data = await res.json();
          setKeys(data.keys || []);
        }
      } catch {
        /* non-critical */
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const activeKeys = keys.filter((k) => k.status === "active");

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
        Usage
      </div>
      <h1
        style={{
          fontFamily: "var(--font-head)",
          fontSize: "1.5rem",
          fontWeight: 800,
          color: "var(--white)",
          marginBottom: "0.5rem",
        }}
      >
        API Key Usage
      </h1>
      <p
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "0.78rem",
          color: "var(--muted)",
          marginBottom: "1.5rem",
          maxWidth: "640px",
          lineHeight: 1.6,
        }}
      >
        Monitor your trial key usage. Quotas are enforced server-side. Upgrade to{" "}
        <a href={CTAS.upgrade.href} style={{ color: "var(--crimson-hi)" }}>
          Hosted Pro
        </a>{" "}
        for higher limits and production access.
      </p>

      {loading ? (
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "0.82rem",
            color: "var(--muted)",
            padding: "2rem 0",
          }}
        >
          Loading usage data…
        </div>
      ) : keys.length === 0 ? (
        <div
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            padding: "2rem",
            maxWidth: "480px",
          }}
        >
          <p
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "0.82rem",
              color: "var(--silver)",
              marginBottom: "1rem",
            }}
          >
            No API keys yet. Generate a trial key to start using the hosted API.
          </p>
          <a
            href="/dashboard/keys"
            className="btn-primary"
            style={{ fontSize: "0.82rem" }}
          >
            Generate Trial Key
          </a>
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
            gap: "1rem",
          }}
        >
          {keys.map((k) => {
            const pct =
              k.monthly_quota > 0
                ? Math.min(100, Math.round((k.requests_used / k.monthly_quota) * 100))
                : 0;
            const isOver = k.requests_used >= k.monthly_quota;
            const barColor = isOver
              ? "var(--crimson-hi)"
              : pct > 80
                ? "#e67e22"
                : "var(--green)";

            return (
              <div
                key={k.id}
                style={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  padding: "1.25rem",
                  opacity: k.status === "revoked" ? 0.5 : 1,
                }}
              >
                {/* Header */}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    marginBottom: "0.75rem",
                  }}
                >
                  <div>
                    <div
                      style={{
                        fontFamily: "var(--font-head)",
                        fontSize: "1rem",
                        fontWeight: 700,
                        color: "var(--white)",
                        marginBottom: "0.2rem",
                      }}
                    >
                      {k.name}
                    </div>
                    <div
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "0.72rem",
                        color: "var(--muted)",
                      }}
                    >
                      {k.key_prefix}
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: "0.35rem" }}>
                    <span
                      style={{
                        display: "inline-block",
                        padding: "0.15rem 0.5rem",
                        fontSize: "0.68rem",
                        fontWeight: 600,
                        letterSpacing: "0.05em",
                        background: "rgba(255,255,255,0.06)",
                        color: "var(--muted)",
                        textTransform: "uppercase",
                      }}
                    >
                      {k.plan}
                    </span>
                    <span
                      style={{
                        display: "inline-block",
                        padding: "0.15rem 0.5rem",
                        fontSize: "0.68rem",
                        fontWeight: 600,
                        letterSpacing: "0.05em",
                        background:
                          k.status === "active"
                            ? "rgba(46,184,122,0.12)"
                            : "rgba(176,34,54,0.15)",
                        color:
                          k.status === "active" ? "var(--green)" : "var(--crimson-hi)",
                        textTransform: "uppercase",
                      }}
                    >
                      {k.status}
                    </span>
                  </div>
                </div>

                {/* Usage bar */}
                <div
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.75rem",
                    color: "var(--silver)",
                    marginBottom: "0.35rem",
                    display: "flex",
                    justifyContent: "space-between",
                  }}
                >
                  <span>
                    {k.requests_used.toLocaleString()} / {k.monthly_quota.toLocaleString()}{" "}
                    requests
                  </span>
                  <span style={{ color: barColor }}>{pct}%</span>
                </div>
                <div
                  style={{
                    height: "6px",
                    background: "var(--surface-2)",
                    marginBottom: "1rem",
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      height: "100%",
                      width: `${pct}%`,
                      background: barColor,
                      transition: "width 0.3s",
                    }}
                  />
                </div>

                {/* Details */}
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: "0.5rem 1rem",
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.72rem",
                  }}
                >
                  {[
                    { label: "Plan", value: k.plan },
                    { label: "Status", value: k.status },
                    {
                      label: "Period start",
                      value: k.period_start?.slice(0, 10) || "—",
                    },
                    {
                      label: "Period end",
                      value: k.period_end?.slice(0, 10) || "—",
                    },
                    {
                      label: "Created",
                      value: k.created_at?.slice(0, 10) || "—",
                    },
                    {
                      label: "Last used",
                      value: k.last_used_at?.slice(0, 10) || "—",
                    },
                  ].map((item) => (
                    <div key={item.label}>
                      <div style={{ color: "var(--muted)", marginBottom: "0.15rem" }}>
                        {item.label}
                      </div>
                      <div style={{ color: "var(--silver)" }}>{item.value}</div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Upgrade prompt */}
      {activeKeys.length > 0 && (
        <div
          style={{
            marginTop: "1.5rem",
            padding: "1rem 1.25rem",
            background: "var(--surface)",
            border: "1px solid var(--border)",
            maxWidth: "640px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "0.75rem",
          }}
        >
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "0.78rem",
              color: "var(--silver)",
              lineHeight: 1.6,
            }}
          >
            Need higher quotas or production access?
          </div>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <a
              href={CTAS.upgrade.href}
              className="btn-primary"
              style={{ fontSize: "0.78rem", padding: "0.45rem 1rem" }}
            >
              Upgrade to Hosted Pro
            </a>
            <a
              href={`mailto:${CTAS.upgrade.href.includes("mailto:") ? "" : "info@aletheia-core.com?subject=Enterprise"}`}
              className="btn-ghost"
              style={{ fontSize: "0.78rem", padding: "0.45rem 1rem", color: "var(--silver)" }}
            >
              Contact for Enterprise
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
