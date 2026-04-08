"use client";

import { useState } from "react";

/* ------------------------------------------------------------------ */
/* Default policy                                                     */
/* ------------------------------------------------------------------ */

const DEFAULT_POLICY = `{
  "policy_version": "1.5.2",
  "restricted_actions": [
    "Transfer_Funds",
    "Approve_Loan_Disbursement",
    "Modify_Auth_Registry",
    "Initiate_ACH",
    "Open_External_Socket",
    "Bulk_Delete_Resource"
  ],
  "intent_threshold": 0.55,
  "grey_zone_lower": 0.40,
  "grey_zone_keyword_min": 2,
  "rate_limit_per_second": 10,
  "receipt_signing": "hmac-sha256",
  "manifest_signing": "ed25519",
  "mode": "active"
}`;

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
  const [editorContent, setEditorContent] = useState(DEFAULT_POLICY);
  const [parseError, setParseError] = useState<string | null>(null);
  const [parsed, setParsed] = useState<Record<string, unknown> | null>(() => {
    try {
      return JSON.parse(DEFAULT_POLICY);
    } catch {
      return null;
    }
  });

  function handleEditorChange(value: string) {
    setEditorContent(value);
    setParseError(null);
    try {
      const obj = JSON.parse(value);
      if (typeof obj !== "object" || obj === null) {
        setParseError("Policy must be a JSON object.");
        setParsed(null);
        return;
      }
      setParsed(obj as Record<string, unknown>);
    } catch (e) {
      setParseError(e instanceof Error ? e.message : "Invalid JSON");
      setParsed(null);
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
        Edit the policy manifest. Changes require re-signing with Ed25519 before deployment.
      </p>

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
        {/* Editor pane */}
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
            Editor
          </div>
          <textarea
            value={editorContent}
            onChange={(e) => handleEditorChange(e.target.value)}
            spellCheck={false}
            style={{
              flex: 1,
              background: "#09090b",
              color: "var(--silver)",
              fontFamily: "var(--font-mono)",
              fontSize: "0.82rem",
              lineHeight: 1.7,
              border: "none",
              padding: "1rem",
              resize: "none",
              outline: "none",
              width: "100%",
              borderRadius: 0,
            }}
          />
          {parseError && (
            <div
              style={{
                padding: "0.5rem 1rem",
                background: "rgba(176,34,54,0.1)",
                borderTop: "1px solid var(--crimson-hi)",
                fontFamily: "var(--font-mono)",
                fontSize: "0.75rem",
                color: "var(--crimson-hi)",
              }}
            >
              Parse error: {parseError}
            </div>
          )}
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
            {parsed ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                {Object.entries(parsed).map(([key, value]) => (
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
                Fix JSON syntax errors to see field reference.
              </div>
            )}
          </div>
        </div>
      </div>

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
