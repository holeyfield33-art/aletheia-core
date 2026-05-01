import type { Metadata } from "next";
import { PRODUCT, URLS } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "Accessibility Statement",
  description: `Accessibility commitment and WCAG conformance statement for ${PRODUCT.name}.`,
};

export default function AccessibilityPage() {
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
        Accessibility Statement
      </h1>
      <p
        style={{
          color: "var(--muted)",
          fontSize: "0.82rem",
          marginBottom: "2rem",
        }}
      >
        Last updated: April 13, 2026
      </p>

      <h2 style={h2}>Our Commitment</h2>
      <p style={p}>
        {PRODUCT.copyrightHolder} is committed to ensuring digital accessibility
        for people with disabilities. We strive to conform to the Web Content
        Accessibility Guidelines (WCAG) 2.1 at Level AA and are continually
        improving the user experience for everyone.
      </p>

      <h2 style={h2}>Current Measures</h2>
      <p style={p}>We have implemented the following accessibility features:</p>
      <ul style={ul}>
        <li>
          <strong style={{ color: "var(--white)" }}>Semantic HTML:</strong>{" "}
          Proper use of headings, landmarks (&lt;main&gt;, &lt;nav&gt;,
          &lt;footer&gt;, &lt;section&gt;), form labels, and native interactive
          elements.
        </li>
        <li>
          <strong style={{ color: "var(--white)" }}>
            Keyboard navigation:
          </strong>{" "}
          All interactive elements are focusable and operable via keyboard.
          Focus states are visually distinct (crimson outline with offset).
        </li>
        <li>
          <strong style={{ color: "var(--white)" }}>Color contrast:</strong>{" "}
          Text-to-background contrast ratios meet WCAG AA requirements. Primary
          foreground (#f0eee8) on background (#080a0c) achieves approximately
          15:1 ratio.
        </li>
        <li>
          <strong style={{ color: "var(--white)" }}>Form accessibility:</strong>{" "}
          All form inputs have associated labels. Error messages are displayed
          inline and connected to their respective fields.
        </li>
        <li>
          <strong style={{ color: "var(--white)" }}>Responsive design:</strong>{" "}
          The interface adapts to various screen sizes and supports text
          resizing up to 200% without loss of content.
        </li>
        <li>
          <strong style={{ color: "var(--white)" }}>ARIA attributes:</strong>{" "}
          Dismiss buttons and interactive controls include appropriate
          aria-label attributes.
        </li>
      </ul>

      <h2 style={h2}>Known Limitations</h2>
      <p style={p}>
        We are aware of the following accessibility limitations and are working
        to address them:
      </p>
      <ul style={ul}>
        <li>
          Some dynamically loaded content (audit log tables, demo results) may
          not announce changes to screen readers via aria-live regions. We are
          adding these progressively.
        </li>
        <li>
          The receipt viewer on the verify page uses a plain textarea that may
          benefit from additional screen reader context.
        </li>
        <li>
          Color-coded decision badges (green/red) also display text labels
          (PROCEED/DENIED) to ensure information is not conveyed by color alone.
        </li>
      </ul>

      <h2 style={h2}>Feedback</h2>
      <p style={p}>
        We welcome your feedback on the accessibility of {PRODUCT.name}. If you
        encounter accessibility barriers or have suggestions for improvement,
        please contact us:
      </p>
      <ul style={ul}>
        <li>
          Email:{" "}
          <a href={URLS.contact} style={{ color: "var(--crimson-hi)" }}>
            {URLS.contactEmail}
          </a>
        </li>
        <li>Subject line: &quot;Accessibility Feedback&quot;</li>
      </ul>

      <h2 style={h2}>Remediation</h2>
      <p style={p}>
        We will acknowledge accessibility reports within 5 business days and aim
        to resolve reported issues within 30 days. If a fix requires more time,
        we will provide a timeline and interim workaround where possible.
      </p>

      <h2 style={h2}>Assessment Approach</h2>
      <p style={p}>
        We assess accessibility through a combination of: automated testing
        tools, manual keyboard navigation testing, screen reader testing, and
        review against WCAG 2.1 Level AA success criteria.
      </p>
    </>
  );
}
