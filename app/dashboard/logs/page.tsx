"use client";

/* ------------------------------------------------------------------ */
/* Audit Logs — Placeholder for trial users                           */
/* Audit log storage exists on the backend (core/audit.py writes      */
/* structured JSON lines). Dashboard log viewing is being finalized   */
/* for Hosted Pro. This page replaces the former mock-data display.   */
/* ------------------------------------------------------------------ */

import { CTAS } from "@/lib/site-config";

export default function LogsPage() {
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
        Audit Logs
      </div>
      <h1
        style={{
          fontFamily: "var(--font-head)",
          fontSize: "1.5rem",
          fontWeight: 800,
          color: "var(--white)",
          marginBottom: "1.25rem",
        }}
      >
        Decision Receipts
      </h1>

      {/* Placeholder notice */}
      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          padding: "2rem",
          maxWidth: "640px",
          marginBottom: "1.5rem",
        }}
      >
        <div
          style={{
            fontFamily: "var(--font-head)",
            fontSize: "1.05rem",
            fontWeight: 700,
            color: "var(--white)",
            marginBottom: "0.75rem",
          }}
        >
          Audit Logs — Coming with Hosted Pro
        </div>
        <p
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "0.82rem",
            color: "var(--silver)",
            lineHeight: 1.7,
            marginBottom: "1rem",
          }}
        >
          Audit Logs are being finalized for Hosted Pro. Trial users can
          generate keys and test the API today while self-serve log viewing
          is rolled out.
        </p>
        <p
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "0.82rem",
            color: "var(--silver)",
            lineHeight: 1.7,
            marginBottom: "1.25rem",
          }}
        >
          Every decision is already signed and logged on the backend. Hosted Pro
          subscribers will get 30-day audit log retention with a dashboard viewer,
          export to JSONL, and receipt verification.
        </p>
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <a
            href="/dashboard/keys"
            className="btn-primary"
            style={{ textAlign: "center", fontSize: "0.82rem" }}
          >
            Get Trial API Key
          </a>
          <a
            href={CTAS.upgrade.href}
            className="btn-secondary"
            style={{ textAlign: "center", fontSize: "0.82rem" }}
          >
            Upgrade to Hosted Pro
          </a>
        </div>
      </div>

      {/* What's available now */}
      <div
        style={{
          padding: "1rem 1.25rem",
          background: "var(--surface)",
          border: "1px solid var(--border)",
          maxWidth: "640px",
        }}
      >
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "0.72rem",
            color: "var(--muted)",
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            marginBottom: "0.5rem",
          }}
        >
          Available now
        </div>
        <ul
          style={{
            listStyle: "none",
            padding: 0,
            margin: 0,
          }}
        >
          {[
            "Generate trial API keys and call the hosted API",
            "View usage and quota on the Usage page",
            "Export signed audit evidence (JSONL) from the Evidence page",
            "Inspect receipts on the Verify page",
          ].map((item) => (
            <li
              key={item}
              style={{
                display: "flex",
                gap: "0.5rem",
                padding: "0.35rem 0",
                fontFamily: "var(--font-mono)",
                fontSize: "0.78rem",
                color: "var(--silver)",
              }}
            >
              <span style={{ color: "var(--green)", flexShrink: 0 }}>✓</span>
              {item}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
