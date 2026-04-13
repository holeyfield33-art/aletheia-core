import type { Metadata } from "next";
import { PRODUCT, URLS } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "Acceptable Use Policy",
  description: `Acceptable Use Policy for ${PRODUCT.name}.`,
};

const EFFECTIVE_DATE = "April 13, 2026";

export default function AcceptableUsePage() {
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
        Acceptable Use Policy
      </h1>
      <p style={{ color: "var(--muted)", fontSize: "0.82rem", marginBottom: "2rem" }}>
        Effective: {EFFECTIVE_DATE} · Last updated: {EFFECTIVE_DATE}
      </p>

      <p style={p}>
        This Acceptable Use Policy (&quot;AUP&quot;) applies to all users of {PRODUCT.name}. It supplements
        our <a href="/legal/terms" style={{ color: "var(--crimson-hi)" }}>Terms of Service</a> and is
        incorporated by reference.
      </p>

      <h2 style={h2}>1. Prohibited Uses</h2>
      <p style={p}>You may not use {PRODUCT.name} to:</p>
      <ul style={ul}>
        <li>Attempt to bypass, evade, or reverse-engineer security controls, the semantic veto engine, sandbox patterns, or policy enforcement mechanisms.</li>
        <li>Submit payloads designed to exfiltrate the policy manifest, alias bank, or internal detection rules.</li>
        <li>Conduct automated scanning, enumeration, or probing of the audit endpoint beyond published rate limits.</li>
        <li>Use the API to process data for which you do not have lawful rights or authorization.</li>
        <li>Resell, redistribute, or sublicense API access without a written agreement from us.</li>
        <li>Facilitate financial fraud, unauthorized access to systems, identity theft, or data theft.</li>
        <li>Submit content that is illegal, infringes third-party rights, or contains malware intended for distribution.</li>
        <li>Impersonate another person or entity, or misrepresent your affiliation with any person or entity.</li>
        <li>Interfere with the availability or performance of the service for other users.</li>
        <li>Use the service in any manner that violates applicable local, state, national, or international law.</li>
      </ul>

      <h2 style={h2}>2. Security Research</h2>
      <p style={p}>
        We welcome responsible security research. If you discover a vulnerability, please report it
        per our <a href={`${URLS.github}/blob/main/SECURITY.md`} style={{ color: "var(--crimson-hi)" }}>Security Policy</a>{" "}
        rather than exploiting it. Good-faith security research conducted in compliance with our
        disclosure policy is not a violation of this AUP.
      </p>

      <h2 style={h2}>3. Enforcement</h2>
      <p style={p}>Violations of this AUP may result in:</p>
      <ul style={ul}>
        <li><strong style={{ color: "var(--white)" }}>First violation:</strong> Written warning and request to cease the prohibited activity.</li>
        <li><strong style={{ color: "var(--white)" }}>Repeated or serious violations:</strong> Temporary suspension of API access.</li>
        <li><strong style={{ color: "var(--white)" }}>Egregious violations:</strong> Immediate and permanent termination of your account without prior notice.</li>
      </ul>
      <p style={p}>
        We reserve the right to determine what constitutes a violation and to take action at our sole discretion.
      </p>

      <h2 style={h2}>4. Reporting</h2>
      <p style={p}>
        To report a violation of this policy, contact us at:{" "}
        <a href={URLS.contact} style={{ color: "var(--crimson-hi)" }}>{URLS.contactEmail}</a>
      </p>
    </>
  );
}
