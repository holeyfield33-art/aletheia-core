import type { Metadata } from "next";
import { PRODUCT, URLS } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "Subscription & Billing Terms",
  description: `Subscription and billing terms for ${PRODUCT.name} hosted plans.`,
};

const EFFECTIVE_DATE = "April 13, 2026";

export default function BillingTermsPage() {
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
        Subscription &amp; Billing Terms
      </h1>
      <p style={{ color: "var(--muted)", fontSize: "0.82rem", marginBottom: "2rem" }}>
        Effective: {EFFECTIVE_DATE} · Last updated: {EFFECTIVE_DATE}
      </p>

      <p style={p}>
        These Subscription &amp; Billing Terms apply to paid plans for {PRODUCT.name} and supplement
        our <a href="/legal/terms" style={{ color: "var(--crimson-hi)" }}>Terms of Service</a>. These terms
        comply with the California Automatic Renewal Law (Cal. Bus. &amp; Prof. Code §§ 17600–17606).
      </p>

      <h2 style={h2}>1. Plans &amp; Pricing</h2>
      <ul style={ul}>
        <li><strong style={{ color: "var(--white)" }}>Community (Free):</strong> Open-source self-hosted. No account required.</li>
        <li><strong style={{ color: "var(--white)" }}>Trial (Free):</strong> 1,000 API requests per month. No payment required. No automatic conversion to a paid plan.</li>
        <li><strong style={{ color: "var(--white)" }}>Pro ($49/month):</strong> 100,000 API requests per month. Billed monthly as a recurring charge via Stripe.</li>
        <li><strong style={{ color: "var(--white)" }}>Enterprise (Custom):</strong> Custom pricing by arrangement. Contact <a href={URLS.contact} style={{ color: "var(--crimson-hi)" }}>{URLS.contactEmail}</a>.</li>
      </ul>

      <h2 style={h2}>2. Recurring Charges &amp; Consent</h2>
      <p style={p}>
        <strong style={{ color: "var(--white)" }}>Clear disclosure:</strong> The Pro plan is a recurring
        monthly subscription at $49.00 USD per month, charged to the payment method you provide at checkout.
      </p>
      <p style={p}>
        <strong style={{ color: "var(--white)" }}>Affirmative consent:</strong> By clicking
        &quot;Subscribe&quot; at checkout, you affirmatively consent to the recurring charge described above.
        Your subscription will automatically renew each month until cancelled.
      </p>

      <h2 style={h2}>3. Free Trial</h2>
      <p style={p}>
        The Trial plan is free and does not require a payment method. There is no automatic conversion from
        the Trial plan to a paid plan. You must explicitly choose to upgrade and provide payment information
        to start a Pro subscription.
      </p>

      <h2 style={h2}>4. Cancellation</h2>
      <p style={p}>You may cancel your Pro subscription at any time by:</p>
      <ul style={ul}>
        <li>Using the Stripe customer portal (linked from your dashboard)</li>
        <li>Contacting us at <a href={URLS.contact} style={{ color: "var(--crimson-hi)" }}>{URLS.contactEmail}</a></li>
      </ul>
      <p style={p}>
        Cancellation takes effect at the end of the current billing period. You will retain Pro access until
        then. After cancellation, your account reverts to the Trial plan with Trial-level quotas.
      </p>

      <h2 style={h2}>5. Refunds</h2>
      <ul style={ul}>
        <li>If you cancel within the first 14 days of your initial Pro subscription, you may request a full refund by contacting us.</li>
        <li>After the 14-day period, no prorated refunds are provided for partial months.</li>
        <li>Refund requests should be directed to <a href={URLS.contact} style={{ color: "var(--crimson-hi)" }}>{URLS.contactEmail}</a>.</li>
      </ul>

      <h2 style={h2}>6. Price Changes</h2>
      <p style={p}>
        We will provide at least 30 days&apos; advance notice via email before any price increase takes effect.
        You may cancel before the price change applies. Continued use after the effective date constitutes
        acceptance of the new price.
      </p>

      <h2 style={h2}>7. Payment Processing</h2>
      <p style={p}>
        All payments are processed by <strong style={{ color: "var(--white)" }}>Stripe, Inc.</strong>{" "}
        We do not store your credit card number or payment credentials. Stripe&apos;s
        terms of service and privacy policy apply to the processing of your payment data.
      </p>

      <h2 style={h2}>8. Failed Payments</h2>
      <p style={p}>
        If a recurring payment fails, Stripe will retry the charge per its retry schedule. If payment
        cannot be collected after repeated attempts, your subscription may be cancelled and your account
        reverted to the Trial plan.
      </p>

      <h2 style={h2}>9. Contact</h2>
      <p style={p}>
        For billing questions, refund requests, or cancellation assistance, contact:{" "}
        <a href={URLS.contact} style={{ color: "var(--crimson-hi)" }}>{URLS.contactEmail}</a>
      </p>
      <p style={p}>
        {PRODUCT.copyrightHolder}<br />
        California, United States
      </p>
    </>
  );
}
