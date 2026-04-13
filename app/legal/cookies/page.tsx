import type { Metadata } from "next";
import { PRODUCT, URLS } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "Cookie & Tracking Disclosure",
  description: `Cookie and tracking disclosure for ${PRODUCT.name}.`,
};

export default function CookiePolicyPage() {
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
        Cookie &amp; Tracking Disclosure
      </h1>
      <p style={{ color: "var(--muted)", fontSize: "0.82rem", marginBottom: "2rem" }}>
        Last updated: April 13, 2026
      </p>

      <h2 style={h2}>Summary</h2>
      <p style={p}>
        {PRODUCT.name} uses <strong style={{ color: "var(--white)" }}>essential cookies only</strong>.
        We do not use tracking cookies, advertising cookies, or third-party analytics that profile users.
        No cookie consent banner is required because we do not use non-essential cookies.
      </p>

      <h2 style={h2}>Cookies We Use</h2>
      <div
        style={{
          border: "1px solid var(--border)",
          borderRadius: "8px",
          overflow: "hidden",
          marginBottom: "1.5rem",
        }}
      >
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: "0.85rem",
          }}
        >
          <thead>
            <tr style={{ background: "var(--surface-2)" }}>
              {["Cookie", "Purpose", "Duration", "Type"].map((col) => (
                <th
                  key={col}
                  style={{
                    padding: "0.75rem 1rem",
                    textAlign: "left",
                    color: "var(--white)",
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.75rem",
                    letterSpacing: "0.05em",
                    textTransform: "uppercase",
                    borderBottom: "1px solid var(--border)",
                  }}
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td style={{ padding: "0.75rem 1rem", color: "var(--white)", fontFamily: "var(--font-mono)", fontSize: "0.82rem", borderBottom: "1px solid var(--border)" }}>
                next-auth.session-token
              </td>
              <td style={{ padding: "0.75rem 1rem", color: "var(--silver)", borderBottom: "1px solid var(--border)" }}>
                Authentication session (JWT)
              </td>
              <td style={{ padding: "0.75rem 1rem", color: "var(--silver)", borderBottom: "1px solid var(--border)" }}>
                7 days
              </td>
              <td style={{ padding: "0.75rem 1rem", color: "var(--silver)", borderBottom: "1px solid var(--border)" }}>
                Essential
              </td>
            </tr>
            <tr>
              <td style={{ padding: "0.75rem 1rem", color: "var(--white)", fontFamily: "var(--font-mono)", fontSize: "0.82rem" }}>
                next-auth.csrf-token
              </td>
              <td style={{ padding: "0.75rem 1rem", color: "var(--silver)" }}>
                CSRF protection for auth forms
              </td>
              <td style={{ padding: "0.75rem 1rem", color: "var(--silver)" }}>
                Session
              </td>
              <td style={{ padding: "0.75rem 1rem", color: "var(--silver)" }}>
                Essential
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <h2 style={h2}>What We Do Not Use</h2>
      <ul style={ul}>
        <li>No Google Analytics, Meta Pixel, or other third-party analytics scripts</li>
        <li>No advertising or remarketing cookies</li>
        <li>No session replay tools (Hotjar, FullStory, etc.)</li>
        <li>No social media tracking widgets</li>
        <li>No cross-site tracking of any kind</li>
      </ul>

      <h2 style={h2}>Do Not Track</h2>
      <p style={p}>
        We honor Do Not Track (DNT) browser signals. Because we do not track users, this signal does
        not change our behavior — we already do not track by default.
      </p>

      <h2 style={h2}>Third-Party Services</h2>
      <p style={p}>
        <strong style={{ color: "var(--white)" }}>Stripe:</strong> When you interact with Stripe checkout,
        Stripe may set its own cookies on the stripe.com domain. These are governed by{" "}
        <a href="https://stripe.com/privacy" style={{ color: "var(--crimson-hi)" }} rel="noopener noreferrer" target="_blank">
          Stripe&apos;s Privacy Policy
        </a>.
      </p>
      <p style={p}>
        <strong style={{ color: "var(--white)" }}>OAuth Providers:</strong> GitHub and Google OAuth flows
        may set cookies on their respective domains during the sign-in process. These are governed by
        those providers&apos; privacy policies.
      </p>

      <h2 style={h2}>Changes</h2>
      <p style={p}>
        If we add analytics or other cookie-setting tools in the future, we will update this page and,
        if required, add a consent mechanism before setting non-essential cookies.
      </p>

      <h2 style={h2}>Contact</h2>
      <p style={p}>
        Questions about our cookie practices:{" "}
        <a href={URLS.contact} style={{ color: "var(--crimson-hi)" }}>{URLS.contactEmail}</a>
      </p>
    </>
  );
}
