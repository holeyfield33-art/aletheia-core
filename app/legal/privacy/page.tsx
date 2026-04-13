import type { Metadata } from "next";
import { PRODUCT, URLS } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: `Privacy Policy for ${PRODUCT.name}. Learn how we collect, use, and protect your data.`,
};

const EFFECTIVE_DATE = "April 13, 2026";

export default function PrivacyPolicyPage() {
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
        Privacy Policy
      </h1>
      <p style={{ color: "var(--muted)", fontSize: "0.82rem", marginBottom: "2rem" }}>
        Effective: {EFFECTIVE_DATE} · Last updated: {EFFECTIVE_DATE}
      </p>

      <p style={p}>
        {PRODUCT.copyrightHolder} (&quot;we,&quot; &quot;us,&quot; or &quot;our&quot;) operates {PRODUCT.name} at{" "}
        <a href={URLS.appBase} style={{ color: "var(--crimson-hi)" }}>{URLS.appBase}</a>.
        This Privacy Policy describes how we collect, use, disclose, and protect personal information
        when you use our website and services.
      </p>

      <h2 style={h2}>1. Information We Collect</h2>
      <p style={p}><strong style={{ color: "var(--white)" }}>Account Information:</strong> When you register, we collect your name (optional), email address, and a password. Passwords are hashed with bcrypt (12 rounds) and never stored in plaintext.</p>
      <p style={p}><strong style={{ color: "var(--white)" }}>OAuth Data:</strong> If you sign in via GitHub or Google, we receive your name, email, and profile image from those providers. We store OAuth tokens as required for authentication.</p>
      <p style={p}><strong style={{ color: "var(--white)" }}>API Usage Data:</strong> When you use our API, we log the action requested, origin, threat score, decision (PROCEED/DENIED), a SHA-256 hash of the payload (not the payload itself), source IP address, and a cryptographic receipt.</p>
      <p style={p}><strong style={{ color: "var(--white)" }}>Billing Information:</strong> If you subscribe to a paid plan, payment processing is handled entirely by Stripe. We store only your Stripe customer ID, subscription ID, and plan status. We do not store credit card numbers, bank account details, or other payment credentials.</p>
      <p style={p}><strong style={{ color: "var(--white)" }}>Technical Data:</strong> IP addresses are collected for rate limiting and abuse prevention. We do not use cookies for tracking. Authentication is handled via HTTP-only, secure, same-site session tokens.</p>

      <h2 style={h2}>2. How We Use Your Information</h2>
      <ul style={ul}>
        <li>Provide, maintain, and improve the {PRODUCT.name} service</li>
        <li>Authenticate your identity and manage your account</li>
        <li>Process payments and manage subscriptions via Stripe</li>
        <li>Enforce rate limits and prevent abuse</li>
        <li>Generate audit logs and cryptographic receipts for security decisions</li>
        <li>Respond to your inquiries and provide support</li>
        <li>Comply with legal obligations</li>
      </ul>

      <h2 style={h2}>3. Information We Share</h2>
      <p style={p}>We do not sell, rent, or trade your personal information. We share data only with:</p>
      <ul style={ul}>
        <li><strong style={{ color: "var(--white)" }}>Stripe</strong> — payment processing (Stripe&apos;s privacy policy applies to payment data)</li>
        <li><strong style={{ color: "var(--white)" }}>Supabase</strong> — database hosting (data stored in your region)</li>
        <li><strong style={{ color: "var(--white)" }}>Vercel</strong> — application hosting and edge delivery</li>
        <li><strong style={{ color: "var(--white)" }}>GitHub / Google</strong> — OAuth authentication (only if you choose to sign in with these providers)</li>
      </ul>
      <p style={p}>We may disclose information if required by law, regulation, legal process, or governmental request.</p>

      <h2 style={h2}>4. Data Retention</h2>
      <ul style={ul}>
        <li><strong style={{ color: "var(--white)" }}>Account data:</strong> Retained until you delete your account. Upon deletion, we initiate a 30-day grace period, after which all personal data is permanently removed.</li>
        <li><strong style={{ color: "var(--white)" }}>Audit logs:</strong> Retained for 90 days, then automatically purged.</li>
        <li><strong style={{ color: "var(--white)" }}>Stripe data:</strong> Retained per Stripe&apos;s data retention policy for regulatory compliance.</li>
      </ul>

      <h2 style={h2}>5. Your California Privacy Rights (CCPA/CPRA)</h2>
      <p style={p}>If you are a California resident, you have the right to:</p>
      <ul style={ul}>
        <li><strong style={{ color: "var(--white)" }}>Right to Know:</strong> Request disclosure of the categories and specific pieces of personal information we have collected. Use the &quot;Export my data&quot; feature in your account settings or contact us.</li>
        <li><strong style={{ color: "var(--white)" }}>Right to Delete:</strong> Request deletion of your personal information. Use the &quot;Delete my account&quot; feature in your account settings or contact us.</li>
        <li><strong style={{ color: "var(--white)" }}>Right to Opt-Out of Sale:</strong> We do not sell personal information. No opt-out is necessary.</li>
        <li><strong style={{ color: "var(--white)" }}>Right to Non-Discrimination:</strong> We will not discriminate against you for exercising your privacy rights.</li>
      </ul>
      <p style={p}>To exercise these rights, email us at{" "}
        <a href={URLS.contact} style={{ color: "var(--crimson-hi)" }}>{URLS.contactEmail}</a> or use the self-service tools in your account settings.
      </p>

      <h2 style={h2}>6. CalOPPA Disclosure</h2>
      <p style={p}>In compliance with the California Online Privacy Protection Act:</p>
      <ul style={ul}>
        <li>This privacy policy is accessible from our homepage via a &quot;Privacy&quot; link.</li>
        <li>We collect: email addresses, names, hashed passwords, IP addresses, API usage metadata, and Stripe billing identifiers.</li>
        <li>We share data with the service providers listed in Section 3.</li>
        <li><strong style={{ color: "var(--white)" }}>Do Not Track:</strong> We honor Do Not Track browser signals. We do not track users across third-party websites. We do not use analytics cookies, advertising pixels, or session replay tools.</li>
      </ul>

      <h2 style={h2}>7. Children&apos;s Privacy</h2>
      <p style={p}>
        {PRODUCT.name} is not directed at individuals under 18 years of age. We do not knowingly collect personal information from anyone under 18. If we learn that we have inadvertently collected such data, we will delete it promptly.
      </p>

      <h2 style={h2}>8. Security</h2>
      <p style={p}>
        We implement industry-standard security measures including: bcrypt password hashing, Ed25519-signed policy manifests, HMAC-signed audit receipts, HTTPS enforcement, Content Security Policy headers, rate limiting, and CSRF protection. For details, see our{" "}
        <a href="/legal/security" style={{ color: "var(--crimson-hi)" }}>Security &amp; Trust</a> page.
      </p>

      <h2 style={h2}>9. Changes to This Policy</h2>
      <p style={p}>
        We may update this Privacy Policy from time to time. We will post the updated policy on this page with a revised &quot;Last updated&quot; date. Material changes will be communicated via email to the address associated with your account.
      </p>

      <h2 style={h2}>10. Contact Us</h2>
      <p style={p}>
        If you have questions about this Privacy Policy or wish to exercise your data rights, contact us at:{" "}
        <a href={URLS.contact} style={{ color: "var(--crimson-hi)" }}>{URLS.contactEmail}</a>
      </p>
      <p style={p}>
        {PRODUCT.copyrightHolder}<br />
        California, United States
      </p>
    </>
  );
}
