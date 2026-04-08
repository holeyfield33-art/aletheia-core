"use client";

import { useState, useCallback } from "react";

/* ------------------------------------------------------------------ */
/* Mock evidence data                                                 */
/* ------------------------------------------------------------------ */

function generateMockEvidence(): string {
  const entries = [
    {
      event_id: "evt_a1b2c3d4",
      timestamp: "2026-04-08T14:32:01Z",
      decision: "DENIED",
      action: "Transfer_Funds",
      origin: "agent-untrusted",
      threat_level: "CRITICAL",
      policy_hash: "sha256:3d4f8e2a1b9c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d",
      payload_sha256: "sha256:9a2b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a",
      signature: "hmac-sha256:7c1e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d",
    },
    {
      event_id: "evt_f6e5d4c3",
      timestamp: "2026-04-08T14:31:44Z",
      decision: "PROCEED",
      action: "fetch_data",
      origin: "monitoring-agent",
      threat_level: "LOW",
      policy_hash: "sha256:3d4f8e2a1b9c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d",
      payload_sha256: "sha256:1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a",
      signature: "hmac-sha256:2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c",
    },
    {
      event_id: "evt_c3d4e5f6",
      timestamp: "2026-04-08T14:30:12Z",
      decision: "SANDBOX_BLOCKED",
      action: "Bulk_Delete_Resource",
      origin: "agent-003",
      threat_level: "CRITICAL",
      policy_hash: "sha256:3d4f8e2a1b9c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d",
      payload_sha256: "sha256:4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a",
      signature: "hmac-sha256:5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a",
    },
  ];
  return entries.map((e) => JSON.stringify(e)).join("\n");
}

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function EvidencePage() {
  const [exported, setExported] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);

  const handleExport = useCallback(() => {
    const jsonl = generateMockEvidence();
    const blob = new Blob([jsonl], { type: "application/x-ndjson" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `aletheia-evidence-${new Date().toISOString().slice(0, 10)}.jsonl`;
    a.click();
    URL.revokeObjectURL(url);
    setExported(true);
    setPreview(jsonl);
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
        Evidence Export
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
        Signed Audit Evidence
      </h1>
      <p
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "0.78rem",
          color: "var(--muted)",
          marginBottom: "2rem",
          maxWidth: "600px",
          lineHeight: 1.6,
        }}
      >
        Export all decision receipts as a JSONL file. Each line is an independently verifiable,
        HMAC-signed audit record. Use this for compliance reviews, incident investigations,
        and third-party audits.
      </p>

      {/* Primary action */}
      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          padding: "2.5rem",
          textAlign: "center",
          marginBottom: "1.5rem",
        }}
      >
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "0.72rem",
            color: "var(--muted)",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            marginBottom: "1.25rem",
          }}
        >
          NIST AI RMF &middot; MEASURE Function
        </div>

        <button
          onClick={handleExport}
          style={{
            background: "var(--crimson)",
            color: "var(--white)",
            border: "none",
            padding: "0.85rem 2.5rem",
            fontFamily: "var(--font-mono)",
            fontSize: "0.88rem",
            fontWeight: 600,
            cursor: "pointer",
            transition: "background 0.2s",
            letterSpacing: "0.02em",
          }}
        >
          Export Signed Audit Evidence (JSONL)
        </button>

        {exported && (
          <div
            style={{
              marginTop: "1rem",
              fontFamily: "var(--font-mono)",
              fontSize: "0.75rem",
              color: "var(--green)",
            }}
          >
            ✓ Evidence exported successfully
          </div>
        )}
      </div>

      {/* Format specification */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "1px",
          background: "var(--border)",
          border: "1px solid var(--border)",
          marginBottom: "1.5rem",
        }}
      >
        {[
          { field: "event_id", desc: "Unique event identifier" },
          { field: "timestamp", desc: "ISO 8601 UTC" },
          { field: "decision", desc: "PROCEED | DENIED | SANDBOX_BLOCKED" },
          { field: "action", desc: "Action identifier evaluated" },
          { field: "origin", desc: "Source agent or client" },
          { field: "threat_level", desc: "Discretised band: LOW-CRITICAL" },
          { field: "policy_hash", desc: "SHA-256 of active policy at decision time" },
          { field: "payload_sha256", desc: "SHA-256 of input payload" },
          { field: "signature", desc: "HMAC-SHA256 receipt signature" },
        ].map(({ field, desc }) => (
          <div key={field} style={{ background: "var(--surface)", padding: "0.65rem 0.85rem" }}>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "0.75rem",
                color: "var(--white)",
                marginBottom: "0.15rem",
              }}
            >
              {field}
            </div>
            <div style={{ fontSize: "0.72rem", color: "var(--muted)" }}>{desc}</div>
          </div>
        ))}
      </div>

      {/* Preview */}
      {preview && (
        <div>
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
            Export Preview
          </div>
          <pre
            style={{
              background: "#09090b",
              border: "1px solid var(--border)",
              padding: "1rem",
              fontFamily: "var(--font-mono)",
              fontSize: "0.72rem",
              color: "var(--silver)",
              overflowX: "auto",
              lineHeight: 1.7,
              whiteSpace: "pre-wrap",
              wordBreak: "break-all",
              maxHeight: "300px",
              overflowY: "auto",
            }}
          >
            {preview}
          </pre>
        </div>
      )}

      {/* Verification note */}
      <div
        style={{
          marginTop: "1.5rem",
          padding: "0.75rem 1rem",
          background: "var(--surface)",
          border: "1px solid var(--border)",
          fontFamily: "var(--font-mono)",
          fontSize: "0.75rem",
          color: "var(--muted)",
          lineHeight: 1.6,
        }}
      >
        Each JSONL line is independently verifiable. Verify receipt integrity with:{" "}
        <code style={{ color: "var(--silver)" }}>
          python -c &quot;import hmac, hashlib, json; ...&quot;
        </code>{" "}
        or use the <a href="/verify" style={{ color: "var(--crimson-hi)" }}>Receipt Viewer</a>.
      </div>
    </div>
  );
}
