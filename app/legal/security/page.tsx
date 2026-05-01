import type { Metadata } from "next";
import { PRODUCT, URLS } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "Security & Trust",
  description: `How ${PRODUCT.name} protects your data and enforces security policies.`,
};

export default function SecurityTrustPage() {
  const h2: React.CSSProperties = {
    fontFamily: "var(--font-head)",
    fontSize: "1.15rem",
    fontWeight: 700,
    color: "var(--white)",
    marginTop: "2.5rem",
    marginBottom: "0.75rem",
  };
  const p: React.CSSProperties = {
    color: "var(--silver)",
    fontSize: "0.9rem",
    lineHeight: 1.75,
    marginBottom: "1rem",
  };
  const ul: React.CSSProperties = {
    color: "var(--silver)",
    fontSize: "0.9rem",
    lineHeight: 1.75,
    paddingLeft: "1.5rem",
    marginBottom: "1rem",
  };

  return (
    <>
      <h1
        style={{
          fontFamily: "var(--font-head)",
          fontSize: "1.8rem",
          fontWeight: 800,
          color: "var(--white)",
          marginBottom: "0.5rem",
        }}
      >
        Security &amp; Trust
      </h1>
      <p
        style={{
          color: "var(--muted)",
          fontSize: "0.82rem",
          marginBottom: "2rem",
        }}
      >
        How {PRODUCT.name} protects your data and operations
      </p>

      <h2 style={h2}>Architecture</h2>
      <p style={p}>
        {PRODUCT.name} uses a tri-agent pipeline to evaluate every API request
        before execution:
      </p>
      <ul style={ul}>
        <li>
          <strong style={{ color: "var(--white)" }}>Scout:</strong> Threat
          intelligence pre-filter detecting instruction smuggling, exfiltration
          patterns, and rotation probing.
        </li>
        <li>
          <strong style={{ color: "var(--white)" }}>Nitpicker:</strong>{" "}
          Polymorphic intent sanitizer with semantic embedding analysis against
          18 blocked patterns.
        </li>
        <li>
          <strong style={{ color: "var(--white)" }}>Judge:</strong>{" "}
          Cryptographic policy enforcer verifying Ed25519-signed manifests and
          running semantic veto analysis against 50+ alias phrases.
        </li>
      </ul>
      <p style={p}>
        All three agents must independently pass for a request to proceed. Any
        single agent can deny. The system fails closed — if any component is
        unavailable, the request is denied.
      </p>

      <h2 style={h2}>Data Protection</h2>
      <ul style={ul}>
        <li>
          <strong style={{ color: "var(--white)" }}>
            Encryption in transit:
          </strong>{" "}
          All connections use TLS 1.2+ with HTTPS enforced. HSTS headers with a
          1-year max-age.
        </li>
        <li>
          <strong style={{ color: "var(--white)" }}>Encryption at rest:</strong>{" "}
          Database hosted on Supabase with encryption at rest enabled.
        </li>
        <li>
          <strong style={{ color: "var(--white)" }}>Password storage:</strong>{" "}
          bcrypt with 12 rounds of salting. Passwords are never stored in
          plaintext or logged.
        </li>
        <li>
          <strong style={{ color: "var(--white)" }}>Payload handling:</strong>{" "}
          API payloads are hashed (SHA-256) for audit logging. Raw payload
          content is not persisted.
        </li>
        <li>
          <strong style={{ color: "var(--white)" }}>API key security:</strong>{" "}
          Keys are HMAC-hashed before storage. Only the key prefix is stored in
          plaintext for identification.
        </li>
      </ul>

      <h2 style={h2}>Access Controls</h2>
      <ul style={ul}>
        <li>JWT-based authentication with 7-day session expiry</li>
        <li>Per-user API key scoping with plan-based quotas</li>
        <li>
          Rate limiting: per-IP sliding window (in-memory or Redis-backed)
        </li>
        <li>
          CSRF protection: Origin/Referer header validation on all
          state-changing requests
        </li>
        <li>
          Content Security Policy, X-Frame-Options (DENY),
          Strict-Transport-Security headers
        </li>
        <li>
          Login brute-force protection: 5 failures per 15 minutes per email
        </li>
        <li>Registration rate limiting: 5 attempts per hour per IP</li>
      </ul>

      <h2 style={h2}>Audit Trail</h2>
      <p style={p}>
        Every security decision is logged with a cryptographic receipt
        containing:
      </p>
      <ul style={ul}>
        <li>Decision (PROCEED / DENIED / SANDBOX_BLOCKED)</li>
        <li>SHA-256 hash of the policy manifest</li>
        <li>SHA-256 hash of the payload</li>
        <li>HMAC signature binding the decision to the specific request</li>
        <li>Timestamp, action, origin, threat score, and unique request ID</li>
      </ul>
      <p style={p}>
        Receipts can be independently verified using the{" "}
        <a href="/verify" style={{ color: "var(--crimson-hi)" }}>
          Receipt Viewer
        </a>
        . Audit logs are exportable in JSONL format from your dashboard.
      </p>

      <h2 style={h2}>Incident Response</h2>
      <ul style={ul}>
        <li>
          <strong style={{ color: "var(--white)" }}>Acknowledgment:</strong>{" "}
          Within 48 hours of a reported vulnerability.
        </li>
        <li>
          <strong style={{ color: "var(--white)" }}>Assessment:</strong> Within
          5 business days.
        </li>
        <li>
          <strong style={{ color: "var(--white)" }}>Critical fix:</strong>{" "}
          Within 14 days for critical severity issues.
        </li>
        <li>
          <strong style={{ color: "var(--white)" }}>Moderate fix:</strong>{" "}
          Within 30 days for moderate severity issues.
        </li>
        <li>
          <strong style={{ color: "var(--white)" }}>
            Coordinated disclosure:
          </strong>{" "}
          Fix released, then public advisory published. Reporter credited unless
          anonymity requested.
        </li>
      </ul>

      <h2 style={h2}>Vulnerability Reporting</h2>
      <p style={p}>
        Report security vulnerabilities by emailing{" "}
        <a href={URLS.contact} style={{ color: "var(--crimson-hi)" }}>
          {URLS.contactEmail}
        </a>
        . Please do not disclose vulnerabilities publicly before a fix is
        available. For full details, see our{" "}
        <a
          href={`${URLS.github}/blob/main/SECURITY.md`}
          style={{ color: "var(--crimson-hi)" }}
        >
          Security Policy
        </a>
        .
      </p>

      <h2 style={h2}>Infrastructure</h2>
      <ul style={ul}>
        <li>
          <strong style={{ color: "var(--white)" }}>Frontend:</strong> Vercel
          (Next.js edge network)
        </li>
        <li>
          <strong style={{ color: "var(--white)" }}>Backend:</strong> Render
          (FastAPI, isolated containers)
        </li>
        <li>
          <strong style={{ color: "var(--white)" }}>Database:</strong> Supabase
          (PostgreSQL with connection pooling)
        </li>
        <li>
          <strong style={{ color: "var(--white)" }}>Payments:</strong> Stripe
          (PCI DSS Level 1 certified)
        </li>
      </ul>

      <h2 style={h2}>Compliance Posture</h2>
      <ul style={ul}>
        <li>
          <strong style={{ color: "var(--white)" }}>CalOPPA:</strong> Privacy
          policy with required disclosures, Do Not Track honored.
        </li>
        <li>
          <strong style={{ color: "var(--white)" }}>CCPA/CPRA:</strong> Right to
          know, right to delete, and right to opt-out supported. Self-service
          tools in account settings.
        </li>
        <li>
          <strong style={{ color: "var(--white)" }}>NIST AI RMF:</strong> Mapped
          across GOVERN, MAP, MEASURE, and MANAGE functions per our{" "}
          <a
            href={`${URLS.github}/blob/main/docs/THREAT_MODEL.md`}
            style={{ color: "var(--crimson-hi)" }}
          >
            Threat Model
          </a>
          .
        </li>
        <li>
          <strong style={{ color: "var(--white)" }}>Open source:</strong>{" "}
          MIT-licensed core available for independent audit at{" "}
          <a href={URLS.github} style={{ color: "var(--crimson-hi)" }}>
            GitHub
          </a>
          .
        </li>
      </ul>
      <p style={p}>
        We are working toward formal SOC 2 Type II and ISO 27001 certification.
        Contact us for details on our timeline.
      </p>

      <h2 style={h2}>Contact</h2>
      <p style={p}>
        Security questions or concerns:{" "}
        <a href={URLS.contact} style={{ color: "var(--crimson-hi)" }}>
          {URLS.contactEmail}
        </a>
      </p>
    </>
  );
}
