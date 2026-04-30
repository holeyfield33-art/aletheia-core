"use client";

import { useState, useEffect } from "react";
import { clientFetch } from "@/lib/client-fetch";

/* ------------------------------------------------------------------ */
/* Policy field descriptions                                          */
/* ------------------------------------------------------------------ */

const FIELD_DOCS: Record<string, string> = {
  policy_version: "Semantic version of the active policy bundle.",
  restricted_actions: "Action identifiers that require Judge evaluation. Exact string match.",
  intent_threshold: "Primary cosine-similarity threshold for the semantic pre-execution block engine (0.0–1.0).",
  grey_zone_lower: "Lower bound of the grey-zone similarity band. Payloads in this range trigger keyword heuristics.",
  grey_zone_keyword_min: "Minimum keyword hits in the grey-zone band to trigger a block.",
  rate_limit_per_second: "Maximum requests per IP per second (sliding window).",
  receipt_signing: "Algorithm used for audit receipt signatures.",
  manifest_signing: "Algorithm used for policy manifest verification.",
  mode: "Runtime mode: 'active' enforces blocks; 'shadow' logs but allows all.",
};

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function PolicyPage() {
  const [policy, setPolicy] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [raw, setRaw] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const res = await clientFetch("/api/policy");
        if (res.ok) {
          const data = await res.json();
          setPolicy(data.policy);
          setRaw(JSON.stringify(data.policy, null, 2));
        }
      } catch {
        /* non-critical */
      } finally {
        setLoading(false);
      }
    })();
  }, []);

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
        Policy Management
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
        security_policy.json
      </h1>
      <p
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "0.78rem",
          color: "var(--muted)",
          marginBottom: "1.5rem",
        }}
      >
        Read-only view of the active security policy manifest. Changes require
        re-signing with Ed25519 via the CLI.
      </p>

      {loading ? (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "1px",
            background: "var(--border)",
            border: "1px solid var(--border)",
            minHeight: "400px",
          }}
        >
          <div style={{ background: "#09090b", padding: "1rem" }}>
            {Array.from({ length: 10 }).map((_, i) => (
              <div key={i} className="skeleton-text" style={{ width: `${55 + (i % 3) * 15}%` }} />
            ))}
          </div>
          <div style={{ background: "var(--surface)", padding: "1rem" }}>
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} style={{ marginBottom: "0.75rem" }}>
                <div className="skeleton-text" style={{ width: "35%" }} />
                <div className="skeleton" style={{ height: "2rem", width: "80%", marginTop: "0.25rem" }} />
              </div>
            ))}
          </div>
        </div>
      ) : (
        <>
          {/* Split screen */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "1px",
              background: "var(--border)",
              border: "1px solid var(--border)",
              minHeight: "500px",
            }}
          >
            {/* JSON view pane */}
            <div style={{ background: "#09090b", display: "flex", flexDirection: "column" }}>
              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.68rem",
                  color: "var(--muted)",
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  padding: "0.6rem 1rem",
                  borderBottom: "1px solid var(--border)",
                  background: "var(--surface)",
                }}
              >
                security_policy.json (read-only)
              </div>
              <pre
                style={{
                  flex: 1,
                  background: "#09090b",
                  color: "var(--silver)",
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.82rem",
                  lineHeight: 1.7,
                  padding: "1rem",
                  margin: 0,
                  overflowY: "auto",
                  whiteSpace: "pre-wrap",
                }}
              >
                {raw || "Policy not found."}
              </pre>
            </div>

            {/* Reference pane */}
            <div style={{ background: "var(--surface)", display: "flex", flexDirection: "column" }}>
              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.68rem",
                  color: "var(--muted)",
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  padding: "0.6rem 1rem",
                  borderBottom: "1px solid var(--border)",
                  background: "var(--surface)",
                }}
              >
                Field Reference
              </div>
              <div style={{ flex: 1, padding: "1rem", overflowY: "auto" }}>
                {policy ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                    {Object.entries(policy).map(([key, value]) => (
                      <div
                        key={key}
                        style={{
                          padding: "0.65rem 0.85rem",
                          background: "#09090b",
                          border: "1px solid var(--border)",
                        }}
                      >
                        <div
                          style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "0.78rem",
                            color: "var(--white)",
                            marginBottom: "0.25rem",
                          }}
                        >
                          {key}
                        </div>
                        <div
                          style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "0.75rem",
                            color: "var(--crimson-hi)",
                            marginBottom: "0.35rem",
                            wordBreak: "break-all",
                          }}
                        >
                          {JSON.stringify(value)}
                        </div>
                        {FIELD_DOCS[key] && (
                          <div
                            style={{
                              fontSize: "0.75rem",
                              color: "var(--muted)",
                              lineHeight: 1.5,
                            }}
                          >
                            {FIELD_DOCS[key]}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.78rem",
                      color: "var(--muted)",
                      padding: "2rem",
                      textAlign: "center",
                    }}
                  >
                    Policy not available.
                  </div>
                )}
              </div>
            </div>
          </div>
        </>
      )}

      <div
        style={{
          marginTop: "1rem",
          padding: "0.75rem 1rem",
          background: "var(--surface)",
          border: "1px solid var(--border)",
          fontFamily: "var(--font-mono)",
          fontSize: "0.75rem",
          color: "var(--muted)",
          lineHeight: 1.6,
        }}
      >
        Changes to the policy manifest require re-signing. Run:{" "}
        <code style={{ color: "var(--silver)" }}>python main.py sign-manifest</code>{" "}
        to update the Ed25519 detached signature before deployment.
      </div>
    </div>
  );
}
