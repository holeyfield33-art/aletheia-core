export default function CLIDocsPage() {
  return (
    <div style={{ maxWidth: "960px", margin: "0 auto", padding: "3rem 2rem" }}>
      <h1
        style={{
          fontSize: "2.2rem",
          fontFamily: "var(--font-head)",
          fontWeight: 800,
          marginBottom: "0.5rem",
        }}
      >
        CLI Reference
      </h1>
      <p
        style={{
          color: "var(--muted)",
          fontSize: "0.95rem",
          marginBottom: "2rem",
        }}
      >
        Command-line interface for local development and deployment operations.
      </p>

      <section style={{ marginBottom: "3rem" }}>
        <h2
          style={{
            fontSize: "1.5rem",
            fontFamily: "var(--font-head)",
            fontWeight: 700,
            marginBottom: "1rem",
          }}
        >
          Installation
        </h2>
        <div
          style={{
            background: "var(--surface-2)",
            border: "1px solid var(--border)",
            borderRadius: "6px",
            padding: "1.25rem",
            fontFamily: "var(--font-mono)",
            fontSize: "0.8rem",
            color: "var(--silver)",
            overflowX: "auto",
          }}
        >
          $ pip install -e .
        </div>
      </section>

      <section style={{ marginBottom: "3rem" }}>
        <h2
          style={{
            fontSize: "1.5rem",
            fontFamily: "var(--font-head)",
            fontWeight: 700,
            marginBottom: "1rem",
          }}
        >
          Commands
        </h2>

        <div style={{ marginBottom: "2.5rem" }}>
          <h3
            style={{
              fontSize: "1.1rem",
              fontWeight: 600,
              marginBottom: "0.75rem",
              color: "var(--crimson-hi)",
            }}
          >
            sign-manifest
          </h3>
          <p style={{ color: "var(--muted)", marginBottom: "1rem" }}>
            Sign the security policy manifest with Ed25519 private key.
          </p>
          <div
            style={{
              background: "var(--surface-2)",
              border: "1px solid var(--border)",
              borderRadius: "6px",
              padding: "1.25rem",
              fontFamily: "var(--font-mono)",
              fontSize: "0.8rem",
              color: "var(--silver)",
              overflowX: "auto",
              marginBottom: "1rem",
            }}
          >
            $ python -m aletheia_cyber_core sign-manifest
          </div>
          <ul
            style={{
              marginLeft: "1.5rem",
              color: "var(--silver)",
              lineHeight: 1.8,
            }}
          >
            <li>
              Reads: <code>manifest/security_policy.json</code>
            </li>
            <li>
              Private key: <code>manifest/security_policy.ed25519.key</code>
            </li>
            <li>
              Output: <code>manifest/security_policy.json.sig</code> (detached)
            </li>
            <li style={{ marginTop: "0.5rem" }}>
              <strong>Use case:</strong> After modifying the policy manifest in
              production, run this command to generate a fresh cryptographic
              signature. Deployed instances verify the signature at startup and
              reject mismatches (fail-closed policy enforcement).
            </li>
          </ul>
        </div>

        <div style={{ marginBottom: "2.5rem" }}>
          <h3
            style={{
              fontSize: "1.1rem",
              fontWeight: 600,
              marginBottom: "0.75rem",
              color: "var(--crimson-hi)",
            }}
          >
            (default) Local Audit
          </h3>
          <p style={{ color: "var(--muted)", marginBottom: "1rem" }}>
            Run a test audit locally (no command specified). Demonstrates the
            tri-agent pipeline (Scout → Nitpicker → Judge).
          </p>
          <div
            style={{
              background: "var(--surface-2)",
              border: "1px solid var(--border)",
              borderRadius: "6px",
              padding: "1.25rem",
              fontFamily: "var(--font-mono)",
              fontSize: "0.8rem",
              color: "var(--silver)",
              overflowX: "auto",
              marginBottom: "1rem",
            }}
          >
            $ python main.py
          </div>
          <p style={{ color: "var(--muted)", marginBottom: "1rem" }}>
            Output shows:
          </p>
          <ul
            style={{
              marginLeft: "1.5rem",
              color: "var(--silver)",
              lineHeight: 1.8,
            }}
          >
            <li>
              <strong>[STAGE 1] Scout Score</strong> — threat level (0–10)
            </li>
            <li>
              <strong>[STAGE 2] Sanitized Payload</strong> — intent cleaning
            </li>
            <li>
              <strong>STATUS</strong> — final decision (✅ PROCEED or 🛑 BLOCKED)
            </li>
          </ul>
        </div>
      </section>

      <section style={{ marginBottom: "3rem" }}>
        <h2
          style={{
            fontSize: "1.5rem",
            fontFamily: "var(--font-head)",
            fontWeight: 700,
            marginBottom: "1rem",
          }}
        >
          Environment Variables
        </h2>
        <div style={{ marginBottom: "1.5rem" }}>
          <code
            style={{
              background: "var(--surface-2)",
              padding: "0.35rem 0.75rem",
              borderRadius: "3px",
              fontFamily: "var(--font-mono)",
              fontSize: "0.85rem",
            }}
          >
            ENVIRONMENT
          </code>
          <p
            style={{
              color: "var(--muted)",
              marginTop: "0.5rem",
            }}
          >
            Set to <code style={{ fontFamily: "var(--font-mono)" }}>production</code> to
            enforce strict validation. Requires ACTIVE_MODE=true and 32+ character
            SIGNING_SECRET. Recommended for production deployments.
          </p>
        </div>
        <div style={{ marginBottom: "1.5rem" }}>
          <code
            style={{
              background: "var(--surface-2)",
              padding: "0.35rem 0.75rem",
              borderRadius: "3px",
              fontFamily: "var(--font-mono)",
              fontSize: "0.85rem",
            }}
          >
            SIGNING_SECRET
          </code>
          <p
            style={{
              color: "var(--muted)",
              marginTop: "0.5rem",
            }}
          >
            (Production only) Random string ≥32 characters for HMAC operations.
            Generate with: <code style={{ fontFamily: "var(--font-mono)" }}>openssl rand -hex 16</code>
          </p>
        </div>
        <div style={{ marginBottom: "1.5rem" }}>
          <code
            style={{
              background: "var(--surface-2)",
              padding: "0.35rem 0.75rem",
              borderRadius: "3px",
              fontFamily: "var(--font-mono)",
              fontSize: "0.85rem",
            }}
          >
            ACTIVE_MODE
          </code>
          <p
            style={{
              color: "var(--muted)",
              marginTop: "0.5rem",
            }}
          >
            Set to <code style={{ fontFamily: "var(--font-mono)" }}>true</code> when ENVIRONMENT=production.
            Confirmation flag to prevent accidental enforcement bypass.
          </p>
        </div>
      </section>

      <section style={{ marginBottom: "3rem" }}>
        <h2
          style={{
            fontSize: "1.5rem",
            fontFamily: "var(--font-head)",
            fontWeight: 700,
            marginBottom: "1rem",
          }}
        >
          Manifest Setup
        </h2>
        <ol
          style={{
            marginLeft: "1.5rem",
            color: "var(--silver)",
            lineHeight: 1.8,
          }}
        >
          <li style={{ marginBottom: "0.75rem" }}>
            Generate Ed25519 keypair (one-time):
            <div
              style={{
                background: "var(--surface-2)",
                border: "1px solid var(--border)",
                borderRadius: "6px",
                padding: "1rem",
                fontFamily: "var(--font-mono)",
                fontSize: "0.8rem",
                color: "var(--silver)",
                overflowX: "auto",
                marginTop: "0.5rem",
              }}
            >
              ssh-keygen -t ed25519 -N "" -f manifest/security_policy.ed25519.key -m pem
            </div>
          </li>
          <li style={{ marginBottom: "0.75rem" }}>
            Extract public key:
            <div
              style={{
                background: "var(--surface-2)",
                border: "1px solid var(--border)",
                borderRadius: "6px",
                padding: "1rem",
                fontFamily: "var(--font-mono)",
                fontSize: "0.8rem",
                color: "var(--silver)",
                overflowX: "auto",
                marginTop: "0.5rem",
              }}
            >
              ssh-keygen -y -f manifest/security_policy.ed25519.key &gt;
              manifest/security_policy.ed25519.pub
            </div>
          </li>
          <li style={{ marginBottom: "0.75rem" }}>
            Edit <code>manifest/security_policy.json</code> with your policy thresholds.
          </li>
          <li style={{ marginBottom: "0.75rem" }}>
            Sign the manifest:
            <div
              style={{
                background: "var(--surface-2)",
                border: "1px solid var(--border)",
                borderRadius: "6px",
                padding: "1rem",
                fontFamily: "var(--font-mono)",
                fontSize: "0.8rem",
                color: "var(--silver)",
                overflowX: "auto",
                marginTop: "0.5rem",
              }}
            >
              python -m aletheia_cyber_core sign-manifest
            </div>
          </li>
          <li>
            Commit {`manifest/security_policy.json.sig`} to version control. Keep
            private key secure and injected via env vars at deploy time.
          </li>
        </ol>
      </section>

      <section>
        <h2
          style={{
            fontSize: "1.5rem",
            fontFamily: "var(--font-head)",
            fontWeight: 700,
            marginBottom: "1rem",
          }}
        >
          Troubleshooting
        </h2>
        <div style={{ marginBottom: "1.5rem" }}>
          <h4
            style={{
              fontSize: "1rem",
              fontWeight: 600,
              marginBottom: "0.5rem",
              color: "var(--crimson-hi)",
            }}
          >
            ManifestTamperedError
          </h4>
          <p style={{ color: "var(--muted)" }}>
            Signature verification failed. Ensure the private key matches the
            public key in the manifest, and re-run
            <code style={{ fontFamily: "var(--font-mono)" }}> sign-manifest</code>.
          </p>
        </div>
        <div style={{ marginBottom: "1.5rem" }}>
          <h4
            style={{
              fontSize: "1rem",
              fontWeight: 600,
              marginBottom: "0.5rem",
              color: "var(--crimson-hi)",
            }}
          >
            FATAL: Production running without ACTIVE_MODE=true
          </h4>
          <p style={{ color: "var(--muted)" }}>
            Set ACTIVE_MODE=true in your deployment environment when
            ENVIRONMENT=production.
          </p>
        </div>
        <div>
          <h4
            style={{
              fontSize: "1rem",
              fontWeight: 600,
              marginBottom: "0.5rem",
              color: "var(--crimson-hi)",
            }}
          >
            FATAL: Production missing SIGNING_SECRET
          </h4>
          <p style={{ color: "var(--muted)" }}>
            In production, set SIGNING_SECRET to a random string ≥32 characters.
          </p>
        </div>
      </section>
    </div>
  );
}

export const metadata = {
  title: "CLI Reference",
  description: "Command-line interface documentation for Aletheia Core.",
};
