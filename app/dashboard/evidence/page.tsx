"use client";

import { useState, useCallback } from "react";
import { useToast } from "@/app/components/Toast";
import { clientFetch } from "@/lib/client-fetch";

/* ------------------------------------------------------------------ */
/* Evidence Export — downloads real audit logs as JSONL                */
/* ------------------------------------------------------------------ */

export default function EvidencePage() {
  const [exported, setExported] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  const handleExport = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await clientFetch("/api/evidence");
      if (!res.ok) {
        setError("Failed to export evidence. Please try again.");
        return;
      }
      const text = await res.text();
      if (!text.trim()) {
        setError("No audit logs to export. Make API requests first.");
        return;
      }
      const blob = new Blob([text], { type: "application/x-ndjson" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `aletheia-evidence-${new Date().toISOString().slice(0, 10)}.jsonl`;
      a.click();
      URL.revokeObjectURL(url);
      setExported(true);
      setPreview(text.split("\n").slice(0, 5).join("\n"));
      toast.success("Evidence exported");
    } catch {
      setError("Network error. Please try again.");
      toast.error("Export failed");
    } finally {
      setLoading(false);
    }
  }, [toast]);

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
          disabled={loading}
          style={{
            background: "var(--crimson)",
            color: "var(--white)",
            border: "none",
            padding: "0.85rem 2.5rem",
            fontFamily: "var(--font-mono)",
            fontSize: "0.88rem",
            fontWeight: 600,
            cursor: loading ? "wait" : "pointer",
            transition: "background 0.2s",
            letterSpacing: "0.02em",
            opacity: loading ? 0.7 : 1,
          }}
        >
          {loading ? "Exporting…" : "Export Signed Audit Evidence (JSONL)"}
        </button>

        {error && (
          <div
            style={{
              marginTop: "1rem",
              fontFamily: "var(--font-mono)",
              fontSize: "0.75rem",
              color: "var(--crimson-hi)",
            }}
          >
            {error}
          </div>
        )}

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
