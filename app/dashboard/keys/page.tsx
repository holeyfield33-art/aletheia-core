"use client";

import { useState, useCallback } from "react";

/* ------------------------------------------------------------------ */
/* Types                                                              */
/* ------------------------------------------------------------------ */

interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  mode: "live" | "test";
  created: string;
  lastUsed: string | null;
}

/* ------------------------------------------------------------------ */
/* Mock data                                                          */
/* ------------------------------------------------------------------ */

const INITIAL_KEYS: ApiKey[] = [
  {
    id: "k1",
    name: "Production Agent",
    prefix: "aleth_live_...a3f8",
    mode: "live",
    created: "2026-03-15",
    lastUsed: "2026-04-08",
  },
  {
    id: "k2",
    name: "Staging CI",
    prefix: "aleth_test_...9c1d",
    mode: "test",
    created: "2026-03-22",
    lastUsed: "2026-04-07",
  },
  {
    id: "k3",
    name: "Local Dev",
    prefix: "aleth_test_...e4b2",
    mode: "test",
    created: "2026-04-01",
    lastUsed: null,
  },
];

function generateKeyId(): string {
  const hex = Array.from(crypto.getRandomValues(new Uint8Array(16)))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
  return hex;
}

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function KeysPage() {
  const [keys, setKeys] = useState<ApiKey[]>(INITIAL_KEYS);
  const [showModal, setShowModal] = useState(false);

  /* Modal state */
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeyMode, setNewKeyMode] = useState<"live" | "test">("test");
  const [generatedSecret, setGeneratedSecret] = useState<string | null>(null);
  const [secretCopied, setSecretCopied] = useState(false);

  const handleGenerate = useCallback(() => {
    const raw = generateKeyId();
    const prefix = newKeyMode === "live" ? "aleth_live_" : "aleth_test_";
    const secret = prefix + raw;
    const display = prefix + "..." + raw.slice(-4);

    setGeneratedSecret(secret);
    setKeys((prev) => [
      {
        id: raw.slice(0, 8),
        name: newKeyName || "Unnamed Key",
        prefix: display,
        mode: newKeyMode,
        created: new Date().toISOString().slice(0, 10),
        lastUsed: null,
      },
      ...prev,
    ]);
  }, [newKeyName, newKeyMode]);

  const handleRevoke = useCallback((id: string) => {
    setKeys((prev) => prev.filter((k) => k.id !== id));
  }, []);

  const handleCloseModal = useCallback(() => {
    setShowModal(false);
    setNewKeyName("");
    setNewKeyMode("test");
    setGeneratedSecret(null);
    setSecretCopied(false);
  }, []);

  const handleCopy = useCallback(() => {
    if (generatedSecret) {
      navigator.clipboard.writeText(generatedSecret);
      setSecretCopied(true);
    }
  }, [generatedSecret]);

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
        API Key Management
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
        API Keys
      </h1>
      <p
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "0.78rem",
          color: "var(--muted)",
          marginBottom: "1.5rem",
          maxWidth: "600px",
          lineHeight: 1.6,
        }}
      >
        Manage keys for authenticating against the Aletheia runtime API. All keys are prefixed
        with <code style={{ color: "var(--silver)" }}>aleth_live_</code> or{" "}
        <code style={{ color: "var(--silver)" }}>aleth_test_</code>.
      </p>

      {/* Generate button */}
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
          marginBottom: "1.5rem",
        }}
      >
        + Generate New Key
      </button>

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
              {["Name", "Prefix", "Mode", "Created", "Last Used", ""].map((h) => (
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
            {keys.map((k) => (
              <tr
                key={k.id}
                style={{ borderBottom: "1px solid var(--border)" }}
              >
                <td style={{ padding: "0.55rem 0.75rem", color: "var(--white)" }}>{k.name}</td>
                <td style={{ padding: "0.55rem 0.75rem", color: "var(--silver)" }}>{k.prefix}</td>
                <td style={{ padding: "0.55rem 0.75rem" }}>
                  <span
                    style={{
                      display: "inline-block",
                      padding: "0.15rem 0.5rem",
                      fontSize: "0.68rem",
                      fontWeight: 600,
                      letterSpacing: "0.05em",
                      background: k.mode === "live" ? "rgba(139,26,42,0.25)" : "rgba(255,255,255,0.06)",
                      color: k.mode === "live" ? "var(--crimson-hi)" : "var(--muted)",
                    }}
                  >
                    {k.mode.toUpperCase()}
                  </span>
                </td>
                <td style={{ padding: "0.55rem 0.75rem", color: "var(--muted)" }}>{k.created}</td>
                <td style={{ padding: "0.55rem 0.75rem", color: "var(--muted)" }}>
                  {k.lastUsed || "—"}
                </td>
                <td style={{ padding: "0.55rem 0.75rem", textAlign: "right" }}>
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
                </td>
              </tr>
            ))}
            {keys.length === 0 && (
              <tr>
                <td
                  colSpan={6}
                  style={{
                    padding: "2rem",
                    textAlign: "center",
                    color: "var(--muted)",
                    fontSize: "0.78rem",
                  }}
                >
                  No active keys. Generate a new key to get started.
                </td>
              </tr>
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
        }}
      >
        Keys are hashed at rest using SHA-256. Only the prefix is stored for identification.
        Live keys grant access to enforcement endpoints. Use test keys for staging and development.
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
                  Generate New API Key
                </h2>

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
                  placeholder="e.g. Production Agent"
                  maxLength={64}
                  style={{
                    width: "100%",
                    padding: "0.5rem 0.65rem",
                    background: "var(--surface)",
                    border: "1px solid var(--border)",
                    color: "var(--white)",
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.82rem",
                    marginBottom: "1rem",
                    outline: "none",
                  }}
                />

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
                  Mode
                </label>
                <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1.5rem" }}>
                  {(["test", "live"] as const).map((m) => (
                    <button
                      key={m}
                      onClick={() => setNewKeyMode(m)}
                      style={{
                        flex: 1,
                        padding: "0.5rem",
                        background:
                          newKeyMode === m ? "rgba(139,26,42,0.25)" : "var(--surface)",
                        border:
                          newKeyMode === m
                            ? "1px solid var(--crimson)"
                            : "1px solid var(--border)",
                        color: newKeyMode === m ? "var(--crimson-hi)" : "var(--muted)",
                        fontFamily: "var(--font-mono)",
                        fontSize: "0.78rem",
                        fontWeight: 600,
                        cursor: "pointer",
                        textTransform: "uppercase",
                      }}
                    >
                      {m}
                    </button>
                  ))}
                </div>

                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <button
                    onClick={handleGenerate}
                    style={{
                      flex: 1,
                      background: "var(--crimson)",
                      color: "var(--white)",
                      border: "none",
                      padding: "0.6rem",
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.82rem",
                      fontWeight: 600,
                      cursor: "pointer",
                    }}
                  >
                    Generate
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
                  Key Generated
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
                  We do not store this key in plain text. If lost, it must be rotated.
                  Copy it now — you will not see it again.
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
                    marginBottom: "1rem",
                    userSelect: "all",
                  }}
                >
                  {generatedSecret}
                </div>

                <div style={{ display: "flex", gap: "0.5rem" }}>
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
                    {secretCopied ? "✓ Copied" : "Copy to Clipboard"}
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
