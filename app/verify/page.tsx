"use client";

import { useState } from "react";

type ReceiptFields = {
  decision?: string;
  policy_hash?: string;
  payload_sha256?: string;
  signature?: string;
  issued_at?: string;
  action?: string;
  origin?: string;
  [key: string]: unknown;
};

const EXAMPLE_RECEIPT = `{
  "decision": "DENIED",
  "policy_hash": "sha256:3d4f...",
  "payload_sha256": "sha256:9a2b...",
  "signature": "hmac-sha256:7c1e...",
  "issued_at": "2026-04-07T00:00:00Z",
  "action": "Transfer_Funds",
  "origin": "agent-001"
}`;

export default function VerifyPage() {
  const [input, setInput] = useState("");
  const [parsed, setParsed] = useState<ReceiptFields | null>(null);
  const [parseError, setParseError] = useState<string | null>(null);

  function handleVerify() {
    setParseError(null);
    setParsed(null);

    if (!input.trim()) {
      setParseError("Paste a receipt JSON above.");
      return;
    }

    try {
      const obj = JSON.parse(input);
      if (typeof obj !== "object" || obj === null) {
        setParseError("Receipt must be a JSON object.");
        return;
      }
      setParsed(obj as ReceiptFields);
    } catch {
      setParseError("Could not parse JSON. Check for syntax errors.");
    }
  }

  function handleClear() {
    setInput("");
    setParsed(null);
    setParseError(null);
  }

  const decision = parsed?.decision?.toUpperCase();
  const knownFields: Array<keyof ReceiptFields> = [
    "decision",
    "policy_hash",
    "payload_sha256",
    "signature",
    "issued_at",
    "action",
    "origin",
  ];
  const extraFields = parsed
    ? Object.keys(parsed).filter(
        (k) => !knownFields.includes(k as keyof ReceiptFields)
      )
    : [];

  return (
    <div style={{ maxWidth: "720px", margin: "0 auto", padding: "3rem 1.5rem 5rem" }}>
      {/* Header */}
      <div style={{ marginBottom: "2.5rem" }}>
        <div
          style={{
            display: "inline-block",
            background: "var(--surface-2)",
            border: "1px solid var(--border-hi)",
            color: "var(--muted)",
            fontFamily: "var(--font-mono)",
            fontSize: "0.72rem",
            padding: "0.25rem 0.7rem",
            borderRadius: "4px",
            marginBottom: "1rem",
            letterSpacing: "0.08em",
          }}
        >
          PREVIEW — Receipt Viewer
        </div>
        <h1
          style={{
            fontFamily: "var(--font-head)",
            fontSize: "clamp(1.75rem, 4vw, 2.5rem)",
            fontWeight: 800,
            color: "var(--white)",
            marginBottom: "0.75rem",
          }}
        >
          Receipt Viewer
        </h1>
        <p style={{ color: "var(--silver)", maxWidth: "520px", lineHeight: 1.65 }}>
          Paste an Aletheia audit receipt to inspect its fields. This viewer
          parses and displays receipt structure. Full cryptographic signature
          verification is available in the CLI — run{" "}
          <code
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "0.82rem",
              background: "var(--surface-2)",
              padding: "0.1rem 0.4rem",
              borderRadius: "3px",
            }}
          >
            aletheia-audit verify
          </code>{" "}
          for on-chain HMAC validation.
        </p>
      </div>

      {/* Input area */}
      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "10px",
          padding: "1.75rem",
          marginBottom: "1.25rem",
        }}
      >
        <label htmlFor="receipt-input">Paste receipt JSON</label>
        <textarea
          id="receipt-input"
          rows={10}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={EXAMPLE_RECEIPT}
          style={{ resize: "vertical", minHeight: "160px", marginBottom: "1rem" }}
          spellCheck={false}
        />
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <button
            onClick={handleVerify}
            className="btn-primary"
            disabled={!input.trim()}
            style={{ opacity: !input.trim() ? 0.6 : 1 }}
          >
            Inspect Receipt
          </button>
          {(parsed || parseError || input) && (
            <button onClick={handleClear} className="btn-secondary">
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Error */}
      {parseError && (
        <div
          style={{
            background: "rgba(176,34,54,0.1)",
            border: "1px solid var(--crimson)",
            borderRadius: "8px",
            padding: "1rem 1.25rem",
            marginBottom: "1.25rem",
            color: "var(--silver)",
            fontSize: "0.9rem",
          }}
          role="alert"
        >
          {parseError}
        </div>
      )}

      {/* Parsed result */}
      {parsed && (
        <div
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border-hi)",
            borderRadius: "10px",
            overflow: "hidden",
          }}
          aria-live="polite"
        >
          {/* Decision banner */}
          <div
            style={{
              padding: "1rem 1.75rem",
              borderBottom: "1px solid var(--border)",
              display: "flex",
              alignItems: "center",
              gap: "1rem",
              flexWrap: "wrap",
              background:
                decision === "PROCEED"
                  ? "rgba(46,184,122,0.05)"
                  : "rgba(176,34,54,0.06)",
            }}
          >
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "0.75rem",
                color: "var(--muted)",
                letterSpacing: "0.08em",
                textTransform: "uppercase",
              }}
            >
              Decision
            </span>
            {decision === "PROCEED" ? (
              <span className="badge-proceed">✓ PROCEED</span>
            ) : decision ? (
              <span className="badge-denied">✕ {decision}</span>
            ) : (
              <span className="badge-error">NO DECISION FIELD</span>
            )}
          </div>

          {/* Fields */}
          <div style={{ padding: "1.5rem 1.75rem", display: "grid", gap: "1rem" }}>
            {[
              { key: "policy_hash", label: "Policy Hash" },
              { key: "payload_sha256", label: "Payload SHA-256" },
              { key: "signature", label: "Signature" },
              { key: "issued_at", label: "Issued At" },
              { key: "action", label: "Action" },
              { key: "origin", label: "Origin" },
            ].map(({ key, label }) =>
              parsed[key as keyof ReceiptFields] !== undefined ? (
                <FieldRow
                  key={key}
                  label={label}
                  value={String(parsed[key as keyof ReceiptFields])}
                />
              ) : (
                <FieldRow key={key} label={label} missing />
              )
            )}

            {extraFields.length > 0 && (
              <>
                <hr style={{ border: "none", borderTop: "1px solid var(--border)" }} />
                <div
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.72rem",
                    color: "var(--muted)",
                    letterSpacing: "0.08em",
                    textTransform: "uppercase",
                  }}
                >
                  Additional Fields
                </div>
                {extraFields.map((k) => (
                  <FieldRow
                    key={k}
                    label={k}
                    value={JSON.stringify(parsed[k])}
                  />
                ))}
              </>
            )}
          </div>

          {/* Disclaimer */}
          <div
            style={{
              padding: "1rem 1.75rem",
              borderTop: "1px solid var(--border)",
              background: "var(--surface-2)",
              fontSize: "0.8rem",
              color: "var(--muted)",
            }}
          >
            This viewer parses and displays receipt fields only. It does not
            perform cryptographic HMAC verification — that requires the server
            secret. To verify the signature, use the Aletheia CLI with your
            configured{" "}
            <code
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "0.78rem",
                background: "var(--surface)",
                padding: "0.1rem 0.35rem",
                borderRadius: "3px",
              }}
            >
              ALETHEIA_RECEIPT_SECRET
            </code>
            .
          </div>
        </div>
      )}

      {/* Link back to demo */}
      <p
        style={{
          marginTop: "2.5rem",
          textAlign: "center",
          fontSize: "0.82rem",
          color: "var(--muted)",
        }}
      >
        Don&apos;t have a receipt yet?{" "}
        <a href="/demo" style={{ color: "var(--silver-dim)" }}>
          Generate one in the live demo →
        </a>
      </p>
    </div>
  );
}

function FieldRow({
  label,
  value,
  missing,
}: {
  label: string;
  value?: string;
  missing?: boolean;
}) {
  return (
    <div>
      <div
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "0.72rem",
          color: "var(--muted)",
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          marginBottom: "0.2rem",
        }}
      >
        {label}
      </div>
      {missing ? (
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "0.8rem",
            color: "var(--silver-dim)",
            fontStyle: "italic",
          }}
        >
          — not present in receipt
        </div>
      ) : (
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "0.8rem",
            color: "var(--silver)",
            wordBreak: "break-all",
            background: "var(--surface-2)",
            border: "1px solid var(--border)",
            borderRadius: "4px",
            padding: "0.5rem 0.75rem",
          }}
        >
          {value}
        </div>
      )}
    </div>
  );
}
