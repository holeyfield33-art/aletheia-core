"use client";

import { useState } from "react";
import Link from "next/link";

export default function ReceiptVerificationFlipCard() {
  const [showBack, setShowBack] = useState(false);

  return (
    <section style={{ padding: "0 1.5rem 2.25rem" }}>
      <div className="container" style={{ maxWidth: "1120px" }}>
        <div className="feature-grid" style={{ display: "grid", gridTemplateColumns: "0.9fr 1.1fr", gap: "1rem", alignItems: "center" }}>
          <div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.74rem", color: "var(--muted)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "0.6rem" }}>
              Step 4
            </div>
            <h2 style={{ fontFamily: "var(--font-head)", fontSize: "clamp(1.7rem, 4vw, 2.4rem)", color: "var(--white)", marginBottom: "0.7rem" }}>
              Every decision gets a receipt.
            </h2>
            <p style={{ color: "var(--silver)", lineHeight: 1.7, marginBottom: "1rem" }}>
              Verify the hash. Detect tampering. Prove what happened.
            </p>
            <Link className="btn-primary" href="/verify">
              Verify Receipt Hash
            </Link>
          </div>

          <div
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border-hi)",
              borderRadius: "16px",
              padding: "1.35rem",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", gap: "0.75rem", alignItems: "center", marginBottom: "1rem" }}>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.74rem", color: "var(--muted)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
                Receipt card
              </div>
              <button type="button" className="btn-secondary" onClick={() => setShowBack((value) => !value)}>
                {showBack ? "Show front" : "Flip card"}
              </button>
            </div>

            <div
              style={{
                borderRadius: "14px",
                border: "1px solid var(--border)",
                background: showBack ? "var(--surface-2)" : "var(--crimson-glow)",
                padding: "1.35rem",
                minHeight: "280px",
                display: "grid",
                alignContent: "start",
                gap: "0.8rem",
              }}
            >
              {!showBack ? (
                <>
                  <div style={{ fontFamily: "var(--font-head)", fontSize: "1.3rem", color: "var(--white)" }}>
                    Every ALLOW, REVIEW, or BLOCK decision can create a signed receipt.
                  </div>
                  <p style={{ color: "var(--silver)", lineHeight: 1.7 }}>
                    Use receipts as portable evidence when you need to prove what the system saw,
                    why it blocked an action, and which policy hash was applied.
                  </p>
                </>
              ) : (
                <>
                  <div style={{ fontFamily: "var(--font-head)", fontSize: "1.3rem", color: "var(--white)" }}>
                    Aletheia receipts include verdict, policy hash, action, origin, timestamp, nonce, and payload fingerprint.
                  </div>
                  <p style={{ color: "var(--silver)", lineHeight: 1.7 }}>
                    If someone edits the receipt later, verification fails. The browser page performs a receipt structure and hash check. Full signature validation remains available in the CLI.
                  </p>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
