import type { Metadata } from "next";
import { PRODUCT, URLS } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "Terms of Service",
  description: `Terms of Service for ${PRODUCT.name}.`,
};

const EFFECTIVE_DATE = "April 13, 2026";

export default function TermsPage() {
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
        Terms of Service
      </h1>
      <p
        style={{
          color: "var(--muted)",
          fontSize: "0.82rem",
          marginBottom: "2rem",
        }}
      >
        Effective: {EFFECTIVE_DATE} · Last updated: {EFFECTIVE_DATE}
      </p>

      <p style={p}>
        These Terms of Service (&quot;Terms&quot;) govern your access to and use
        of {PRODUCT.name}, operated by {PRODUCT.copyrightHolder}{" "}
        (&quot;we,&quot; &quot;us,&quot; or &quot;our&quot;). By creating an
        account or using our services, you agree to be bound by these Terms.
      </p>

      <h2 style={h2}>1. Acceptance of Terms</h2>
      <p style={p}>
        By creating an account, you confirm that you have read, understood, and
        agree to these Terms, our{" "}
        <a href="/legal/privacy" style={{ color: "var(--crimson-hi)" }}>
          Privacy Policy
        </a>
        , and our{" "}
        <a href="/legal/acceptable-use" style={{ color: "var(--crimson-hi)" }}>
          Acceptable Use Policy
        </a>
        . If you do not agree, do not use the service.
      </p>

      <h2 style={h2}>2. Eligibility</h2>
      <p style={p}>
        You must be at least 18 years of age and have the legal capacity to
        enter into a binding agreement. By registering, you represent that you
        meet these requirements.
      </p>

      <h2 style={h2}>3. Account Responsibilities</h2>
      <ul style={ul}>
        <li>
          You must provide accurate and complete information when creating your
          account.
        </li>
        <li>
          You are responsible for maintaining the confidentiality of your
          credentials and API keys.
        </li>
        <li>
          You must not share API keys or allow unauthorized access to your
          account.
        </li>
        <li>
          You must notify us immediately at{" "}
          <a href={URLS.contact} style={{ color: "var(--crimson-hi)" }}>
            {URLS.contactEmail}
          </a>{" "}
          if you suspect unauthorized access.
        </li>
      </ul>

      <h2 style={h2}>4. Service Description</h2>
      <p style={p}>
        {PRODUCT.name} provides a runtime audit and pre-execution block layer
        for AI agents, including: cryptographically signed policy enforcement,
        semantic intent analysis, tamper-evident audit receipts, and API-based
        decision logging. The open-source core is available under the MIT
        License. The hosted service is subject to these Terms.
      </p>

      <h2 style={h2}>5. API Usage &amp; Quotas</h2>
      <ul style={ul}>
        <li>
          <strong style={{ color: "var(--white)" }}>Free Plan:</strong> 1,000
          Sovereign Audit Receipts per month, 1 API key.
        </li>
        <li>
          <strong style={{ color: "var(--white)" }}>Scale Plan:</strong> 25,000
          verified decisions per month, up to 10 API keys.
        </li>
        <li>
          <strong style={{ color: "var(--white)" }}>Pro Plan:</strong> 100,000
          verified decisions per month, up to 10 API keys.
        </li>
        <li>
          <strong style={{ color: "var(--white)" }}>Enterprise:</strong> Custom
          limits by arrangement.
        </li>
      </ul>
      <p style={p}>
        Exceeding your plan&apos;s quota will result in rate-limited responses
        until the next billing period. We reserve the right to modify quotas
        with 30 days&apos; notice.
      </p>

      <h2 style={h2}>6. Prohibited Conduct</h2>
      <p style={p}>
        You agree to comply with our{" "}
        <a href="/legal/acceptable-use" style={{ color: "var(--crimson-hi)" }}>
          Acceptable Use Policy
        </a>
        , which is incorporated into these Terms by reference.
      </p>

      <h2 style={h2}>7. Payment Terms</h2>
      <p style={p}>
        Paid plans are governed by our{" "}
        <a href="/legal/billing" style={{ color: "var(--crimson-hi)" }}>
          Subscription &amp; Billing Terms
        </a>
        , which are incorporated into these Terms by reference.
      </p>

      <h2 style={h2}>8. Intellectual Property</h2>
      <p style={p}>
        The {PRODUCT.name} open-source engine is licensed under the MIT License.
        The hosted platform, branding, documentation, and proprietary
        enhancements remain the property of {PRODUCT.copyrightHolder}. Your use
        of the hosted service does not grant you ownership of any intellectual
        property.
      </p>

      <h2 style={h2}>9. Termination</h2>
      <ul style={ul}>
        <li>
          <strong style={{ color: "var(--white)" }}>By you:</strong> You may
          close your account at any time through account settings or by
          contacting us. Active subscriptions will continue until the end of the
          current billing period.
        </li>
        <li>
          <strong style={{ color: "var(--white)" }}>By us:</strong> We may
          suspend or terminate your account immediately for violation of these
          Terms or the Acceptable Use Policy. For termination without cause, we
          will provide 30 days&apos; notice.
        </li>
      </ul>
      <p style={p}>
        Upon termination, your data will be handled in accordance with our{" "}
        <a href="/legal/privacy" style={{ color: "var(--crimson-hi)" }}>
          Privacy Policy
        </a>{" "}
        (30-day grace period, then permanent deletion).
      </p>

      <h2 style={h2}>10. Disclaimers</h2>
      <p style={p}>
        THE SERVICE IS PROVIDED &quot;AS IS&quot; AND &quot;AS AVAILABLE&quot;
        WITHOUT WARRANTIES OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT
        LIMITED TO WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
        PURPOSE, AND NON-INFRINGEMENT. We do not warrant that the service will
        be uninterrupted, error-free, or that it will detect all security
        threats. {PRODUCT.name} is a supplementary security layer and is not a
        substitute for comprehensive security practices or human review.
      </p>

      <h2 style={h2}>11. Limitation of Liability</h2>
      <p style={p}>
        TO THE MAXIMUM EXTENT PERMITTED BY LAW,{" "}
        {PRODUCT.copyrightHolder.toUpperCase()} SHALL NOT BE LIABLE FOR ANY
        INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES
        ARISING FROM YOUR USE OF THE SERVICE. OUR TOTAL LIABILITY SHALL NOT
        EXCEED THE FEES PAID BY YOU IN THE TWELVE (12) MONTHS PRECEDING THE
        CLAIM.
      </p>

      <h2 style={h2}>12. Indemnification</h2>
      <p style={p}>
        You agree to indemnify and hold harmless {PRODUCT.copyrightHolder}, its
        officers, and employees from any claims, damages, or expenses arising
        from your use of the service, your violation of these Terms, or your
        violation of any third-party rights.
      </p>

      <h2 style={h2}>13. Dispute Resolution</h2>
      <p style={p}>
        <strong style={{ color: "var(--white)" }}>Binding Arbitration:</strong>{" "}
        Any dispute arising from these Terms or your use of the service shall be
        resolved by binding arbitration administered by the American Arbitration
        Association (AAA) under its Commercial Arbitration Rules. The
        arbitration shall take place in California, and the arbitrator&apos;s
        decision shall be final and binding.
      </p>
      <p style={p}>
        <strong style={{ color: "var(--white)" }}>Class Action Waiver:</strong>{" "}
        You agree that any dispute resolution proceedings will be conducted only
        on an individual basis and not in a class, consolidated, or
        representative action.
      </p>
      <p style={p}>
        <strong style={{ color: "var(--white)" }}>
          Small Claims Exception:
        </strong>{" "}
        Either party may bring an individual action in small claims court for
        disputes within the court&apos;s jurisdictional limits.
      </p>

      <h2 style={h2}>14. Governing Law</h2>
      <p style={p}>
        These Terms shall be governed by and construed in accordance with the
        laws of the State of California, without regard to its conflict of law
        provisions.
      </p>

      <h2 style={h2}>15. General Provisions</h2>
      <ul style={ul}>
        <li>
          <strong style={{ color: "var(--white)" }}>Severability:</strong> If
          any provision of these Terms is held unenforceable, the remaining
          provisions remain in full force and effect.
        </li>
        <li>
          <strong style={{ color: "var(--white)" }}>Entire Agreement:</strong>{" "}
          These Terms, together with the Privacy Policy, Acceptable Use Policy,
          and Billing Terms, constitute the entire agreement between you and us.
        </li>
        <li>
          <strong style={{ color: "var(--white)" }}>Assignment:</strong> You may
          not assign your rights under these Terms. We may assign our rights to
          a successor entity.
        </li>
        <li>
          <strong style={{ color: "var(--white)" }}>Force Majeure:</strong> We
          shall not be liable for delays caused by events beyond our reasonable
          control.
        </li>
        <li>
          <strong style={{ color: "var(--white)" }}>Waiver:</strong> Our failure
          to enforce any provision does not constitute a waiver of that
          provision.
        </li>
      </ul>

      <h2 style={h2}>16. Contact</h2>
      <p style={p}>
        Questions about these Terms? Contact us at:{" "}
        <a href={URLS.contact} style={{ color: "var(--crimson-hi)" }}>
          {URLS.contactEmail}
        </a>
      </p>
      <p style={p}>
        {PRODUCT.copyrightHolder}
        <br />
        California, United States
      </p>
    </>
  );
}
