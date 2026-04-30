"use client";

import { useState, useCallback, useEffect } from "react";
import { useToast } from "@/app/components/Toast";
import { CTAS, URLS } from "@/lib/site-config";
import { clientFetch, clientFetchResponse, isClientFetchError } from "@/lib/client-fetch";

/* ------------------------------------------------------------------ */
/* Types                                                              */
/* ------------------------------------------------------------------ */

interface ApiKey {
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

interface ApiKeysResponse {
  keys?: ApiKey[];
}

interface CreateApiKeyResponse {
  key: string;
}

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function KeysPage() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /* Modal state */
  const [newKeyName, setNewKeyName] = useState("");
  const [generatedSecret, setGeneratedSecret] = useState<string | null>(null);
  const [secretCopied, setSecretCopied] = useState(false);
  const [generating, setGenerating] = useState(false);
  const toast = useToast();

  /* Fetch keys on mount */
  useEffect(() => {
    fetchKeys();
  }, []);

  const fetchKeys = async () => {
    try {
      const data = await clientFetch<ApiKeysResponse>("/api/keys");
      setKeys(data.keys || []);
    } catch {
      /* non-critical — keys will show empty */
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = useCallback(async () => {
    setGenerating(true);
    setError(null);
    try {
      const data = await clientFetch<CreateApiKeyResponse>("/api/keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newKeyName || "Unnamed Key" }),
      });
      setGeneratedSecret(data.key);
      toast.success("API key generated");
      /* Refresh key list */
      fetchKeys();
    } catch (error) {
      if (isClientFetchError(error) && typeof error.data === "object" && error.data) {
        const payload = error.data as { message?: string; error?: string };
        setError(payload.message || payload.error || "Failed to generate key");
      } else {
        setError("Network error. Try again.");
      }
    } finally {
      setGenerating(false);
    }
  }, [newKeyName, toast]);

  const handleRevoke = useCallback(async (id: string) => {
    try {
      await clientFetchResponse(`/api/keys/${id}`, { method: "DELETE" });
      setKeys((prev) => prev.map((k) => (k.id === id ? { ...k, status: "revoked" } : k)));
      toast.info("Key revoked");
    } catch {
      /* silent */
    }
  }, [toast]);

  const handleCloseModal = useCallback(() => {
    setShowModal(false);
    setNewKeyName("");
    setGeneratedSecret(null);
    setSecretCopied(false);
    setError(null);
  }, []);

  const handleCopy = useCallback(() => {
    if (generatedSecret) {
      navigator.clipboard.writeText(generatedSecret);
      setSecretCopied(true);
      toast.success("Key copied to clipboard");
    }
  }, [generatedSecret, toast]);

  const overlay: React.CSSProperties = {
    position: "fixed",
    inset: 0,
    background: "rgba(0,0,0,0.75)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 1000,
  };

  const modal: React.CSSProperties = {
    background: "#09090b",
    border: "1px solid var(--border)",
    padding: "2rem",
    width: "100%",
    maxWidth: "440px",
  };

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
        Trial API Key Management
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
        Trial API Keys
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
        Trial keys are for evaluation only with limited monthly Sovereign Audit Receipts (1,000/month).
        They are not for production workloads. For production API access with
        retained audit logs, higher quotas, and managed infrastructure, upgrade to{" "}
        <a href={CTAS.upgrade.href} style={{ color: "var(--crimson-hi)" }}>
          Scale or Pro
        </a>.
      </p>

      {/* Usage instructions */}
      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          padding: "1.25rem",
          marginBottom: "1.5rem",
          maxWidth: "640px",
        }}
      >
        <div
          style={{
            fontFamily: "var(--font-head)",
            fontSize: "0.95rem",
            fontWeight: 700,
            color: "var(--white)",
            marginBottom: "0.5rem",
          }}
        >
          How to use your trial key
        </div>
        <p
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "0.78rem",
            color: "var(--silver)",
            lineHeight: 1.7,
            marginBottom: "0.75rem",
          }}
        >
          Use this trial key in the <code style={{ color: "var(--white)" }}>X-API-Key</code>{" "}
          header when calling the hosted API. Trial keys are limited to evaluation
          usage and are not for production workloads.
        </p>

        {/* Quickstart curl example */}
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "0.72rem",
            color: "var(--muted)",
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            marginBottom: "0.35rem",
          }}
        >
          Quickstart
        </div>
        <pre
          style={{
            background: "var(--surface-2)",
            border: "1px solid var(--border)",
            padding: "0.75rem 1rem",
            fontFamily: "var(--font-mono)",
            fontSize: "0.75rem",
            color: "var(--silver)",
            lineHeight: 1.7,
            overflowX: "auto",
            whiteSpace: "pre",
            marginBottom: "0.75rem",
          }}
        >{`curl -X POST ${URLS.appBase}/v1/audit \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: sk_trial_xxxxx" \\
  -d '{
    "payload": "Generate the Q1 revenue report",
    "origin": "monitoring-agent",
    "action": "Read_Report"
  }'`}</pre>

        {/* Common errors */}
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "0.72rem",
            color: "var(--muted)",
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            marginBottom: "0.35rem",
          }}
        >
          Common errors
        </div>
        <ul
          style={{
            listStyle: "none",
            padding: 0,
            margin: 0,
          }}
        >
          {[
            { code: "401", desc: "Missing or invalid X-API-Key header" },
            { code: "403", desc: "Key revoked or action denied by policy" },
            { code: "429", desc: "Rate limit or monthly quota exceeded" },
          ].map((e) => (
            <li
              key={e.code}
              style={{
                display: "flex",
                gap: "0.5rem",
                padding: "0.25rem 0",
                fontFamily: "var(--font-mono)",
                fontSize: "0.75rem",
                color: "var(--silver)",
              }}
            >
              <span style={{ color: "var(--crimson-hi)", fontWeight: 600, minWidth: "28px" }}>
                {e.code}
              </span>
              {e.desc}
            </li>
          ))}
        </ul>
      </div>

      {/* Actions bar */}
      <div style={{ display: "flex", gap: "0.75rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
        <button
          onClick={() => setShowModal(true)}
          style={{
            background: "var(--crimson)",
            color: "var(--white)",
            border: "none",
            padding: "0.6rem 1.5rem",
            fontFamily: "var(--font-mono)",
            fontSize: "0.82rem",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          + Generate Trial Key
        </button>
        <a
          href="/dashboard/usage"
          className="btn-secondary"
          style={{ fontSize: "0.82rem", padding: "0.6rem 1.25rem" }}
        >
          View Usage
        </a>
        <a
          href={CTAS.upgrade.href}
          className="btn-ghost"
          style={{ fontSize: "0.82rem", padding: "0.6rem 1.25rem", color: "var(--silver)" }}
        >
          Upgrade to a paid hosted plan
        </a>
      </div>

      {/* Key table */}
      <div
        style={{
          border: "1px solid var(--border)",
          overflow: "auto",
        }}
      >
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontFamily: "var(--font-mono)",
            fontSize: "0.78rem",
          }}
        >
          <thead>
            <tr style={{ borderBottom: "1px solid var(--border)" }}>
              {["Name", "Prefix", "Plan", "Status", "Created", "Last Used", ""].map((h) => (
                <th
                  key={h}
                  style={{
                    textAlign: "left",
                    padding: "0.6rem 0.75rem",
                    color: "var(--muted)",
                    fontWeight: 500,
                    fontSize: "0.72rem",
                    letterSpacing: "0.06em",
                    textTransform: "uppercase",
                    whiteSpace: "nowrap",
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 3 }).map((_, i) => (
                <tr key={`skel-${i}`} style={{ borderBottom: "1px solid var(--border)" }}>
                  {Array.from({ length: 7 }).map((_, j) => (
                    <td key={j} style={{ padding: "0.55rem 0.65rem" }}>
                      <div className="skeleton-text" style={{ width: j === 0 ? "80%" : "55%" }} />
                    </td>
                  ))}
                </tr>
              ))
            ) : keys.length === 0 ? (
              <tr>
                <td
                  colSpan={7}
                  style={{
                    padding: "2rem",
                    textAlign: "center",
                    color: "var(--muted)",
                    fontSize: "0.78rem",
                  }}
                >
                  No keys yet. Generate a trial key to get started.
                </td>
              </tr>
            ) : (
              keys.map((k) => (
                <tr
                  key={k.id}
                  style={{
                    borderBottom: "1px solid var(--border)",
                    opacity: k.status === "revoked" ? 0.5 : 1,
                  }}
                >
                  <td style={{ padding: "0.55rem 0.75rem", color: "var(--white)" }}>{k.name}</td>
                  <td style={{ padding: "0.55rem 0.75rem", color: "var(--silver)" }}>
                    {k.key_prefix}
                  </td>
                  <td style={{ padding: "0.55rem 0.75rem" }}>
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
                  </td>
                  <td style={{ padding: "0.55rem 0.75rem" }}>
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
                        color: k.status === "active" ? "var(--green)" : "var(--crimson-hi)",
                        textTransform: "uppercase",
                      }}
                    >
                      {k.status}
                    </span>
                  </td>
                  <td style={{ padding: "0.55rem 0.75rem", color: "var(--muted)" }}>
                    {k.created_at?.slice(0, 10) || "—"}
                  </td>
                  <td style={{ padding: "0.55rem 0.75rem", color: "var(--muted)" }}>
                    {k.last_used_at?.slice(0, 10) || "—"}
                  </td>
                  <td style={{ padding: "0.55rem 0.75rem", textAlign: "right" }}>
                    {k.status === "active" && (
                      <button
                        onClick={() => handleRevoke(k.id)}
                        style={{
                          background: "none",
                          border: "1px solid rgba(139,26,42,0.5)",
                          color: "var(--crimson-hi)",
                          padding: "0.25rem 0.75rem",
                          fontFamily: "var(--font-mono)",
                          fontSize: "0.72rem",
                          cursor: "pointer",
                        }}
                      >
                        Revoke
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Security note */}
      <div
        style={{
          marginTop: "1rem",
          padding: "0.65rem 1rem",
          background: "var(--surface)",
          border: "1px solid var(--border)",
          fontFamily: "var(--font-mono)",
          fontSize: "0.72rem",
          color: "var(--muted)",
          lineHeight: 1.6,
          maxWidth: "640px",
        }}
      >
        Keys are hashed at rest using SHA-256. Only the prefix is stored for identification.
        Trial keys are limited to 1,000 Sovereign Audit Receipts per month for evaluation use.
        For production access, managed infrastructure, and higher quotas,{" "}
        <a href={CTAS.upgrade.href} style={{ color: "var(--crimson-hi)" }}>
          upgrade to a paid hosted plan
        </a>.
      </div>

      {/* Modal */}
      {showModal && (
        <div style={overlay} onClick={handleCloseModal}>
          <div style={modal} onClick={(e) => e.stopPropagation()}>
            {!generatedSecret ? (
              <>
                <h2
                  style={{
                    fontFamily: "var(--font-head)",
                    fontSize: "1.1rem",
                    fontWeight: 700,
                    color: "var(--white)",
                    marginBottom: "1.25rem",
                  }}
                >
                  Generate Trial API Key
                </h2>

                {error && (
                  <div
                    style={{
                      background: "rgba(176,34,54,0.15)",
                      border: "1px solid var(--crimson-hi)",
                      padding: "0.5rem 0.75rem",
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.75rem",
                      color: "var(--crimson-hi)",
                      marginBottom: "1rem",
                    }}
                  >
                    {error}
                  </div>
                )}

                <label
                  style={{
                    display: "block",
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.72rem",
                    color: "var(--muted)",
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                    marginBottom: "0.35rem",
                  }}
                >
                  Key Name
                </label>
                <input
                  type="text"
                  value={newKeyName}
                  onChange={(e) => setNewKeyName(e.target.value)}
                  placeholder="e.g. My Evaluation Key"
                  maxLength={64}
                  style={{
                    width: "100%",
                    padding: "0.5rem 0.65rem",
                    background: "var(--surface)",
                    border: "1px solid var(--border)",
                    color: "var(--white)",
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.82rem",
                    marginBottom: "1.5rem",
                    outline: "none",
                  }}
                />

                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <button
                    onClick={handleGenerate}
                    disabled={generating}
                    style={{
                      flex: 1,
                      background: "var(--crimson)",
                      color: "var(--white)",
                      border: "none",
                      padding: "0.6rem",
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.82rem",
                      fontWeight: 600,
                      cursor: generating ? "wait" : "pointer",
                      opacity: generating ? 0.7 : 1,
                    }}
                  >
                    {generating ? "Generating…" : "Generate Trial Key"}
                  </button>
                  <button
                    onClick={handleCloseModal}
                    style={{
                      padding: "0.6rem 1.25rem",
                      background: "none",
                      border: "1px solid var(--border)",
                      color: "var(--muted)",
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.82rem",
                      cursor: "pointer",
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </>
            ) : (
              <>
                <h2
                  style={{
                    fontFamily: "var(--font-head)",
                    fontSize: "1.1rem",
                    fontWeight: 700,
                    color: "var(--white)",
                    marginBottom: "0.75rem",
                  }}
                >
                  Trial Key Generated
                </h2>

                <div
                  style={{
                    background: "rgba(139,26,42,0.12)",
                    border: "1px solid rgba(139,26,42,0.4)",
                    padding: "0.75rem 1rem",
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.74rem",
                    color: "var(--crimson-hi)",
                    lineHeight: 1.6,
                    marginBottom: "1rem",
                  }}
                >
                  This key is shown once only. We store only a SHA-256 hash — if
                  lost, generate a new key. Copy it now.
                </div>

                <div
                  style={{
                    background: "var(--surface)",
                    border: "1px solid var(--border)",
                    padding: "0.75rem 1rem",
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.82rem",
                    color: "var(--white)",
                    wordBreak: "break-all",
                    marginBottom: "0.5rem",
                    userSelect: "all",
                  }}
                >
                  {generatedSecret}
                </div>

                <div
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.72rem",
                    color: "var(--muted)",
                    marginBottom: "1rem",
                    lineHeight: 1.6,
                  }}
                >
                  Use this key in the <code style={{ color: "var(--white)" }}>X-API-Key</code>{" "}
                  header to call the hosted API. Trial: 1,000 Sovereign Audit Receipts/month.
                </div>

                <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                  <button
                    onClick={handleCopy}
                    style={{
                      flex: 1,
                      background: secretCopied ? "rgba(80,200,120,0.15)" : "var(--crimson)",
                      color: secretCopied ? "#50c878" : "var(--white)",
                      border: secretCopied ? "1px solid rgba(80,200,120,0.3)" : "none",
                      padding: "0.6rem",
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.82rem",
                      fontWeight: 600,
                      cursor: "pointer",
                    }}
                  >
                    {secretCopied ? "✓ Copied" : "Copy Key"}
                  </button>
                  <a
                    href="/dashboard/usage"
                    style={{
                      padding: "0.6rem 1rem",
                      background: "none",
                      border: "1px solid var(--border)",
                      color: "var(--silver)",
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.82rem",
                      textDecoration: "none",
                      textAlign: "center",
                    }}
                  >
                    View Usage
                  </a>
                  <button
                    onClick={handleCloseModal}
                    style={{
                      padding: "0.6rem 1.25rem",
                      background: "none",
                      border: "1px solid var(--border)",
                      color: "var(--muted)",
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.82rem",
                      cursor: "pointer",
                    }}
                  >
                    Done
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
