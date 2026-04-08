import type { Metadata } from "next";
import "./globals.css";
import { PRODUCT, URLS } from "@/lib/site-config";

export const metadata: Metadata = {
  title: {
    default: `${PRODUCT.name} — Runtime audit and pre-execution block layer for AI agents`,
    template: `%s | ${PRODUCT.name}`,
  },
  description:
    "Cryptographically signed enforcement, semantic policy hardening, and tamper-evident audit receipts for agentic workflows.",
  keywords: [
    "supply-chain security",
    "malicious code detection",
    "Python security",
    "dependency scanning",
    "runtime security",
    "audit receipts",
    "AI safety",
    "open-source security",
  ],
  openGraph: {
    type: "website",
    url: URLS.appBase,
    siteName: PRODUCT.name,
    title: `${PRODUCT.name} — Runtime audit and pre-execution block layer for AI agents`,
    description:
      "Cryptographically signed enforcement, semantic policy hardening, and tamper-evident audit receipts for agentic workflows.",
  },
  twitter: {
    card: "summary_large_image",
    title: `${PRODUCT.name} — Runtime audit and pre-execution block layer for AI agents`,
    description:
      "Cryptographically signed enforcement, semantic policy hardening, and tamper-evident audit receipts for agentic workflows.",
  },
  metadataBase: new URL(URLS.appBase),
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=JetBrains+Mono:wght@400;500&family=Inter:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
        <link rel="icon" href="/favicon.ico" />
        <link rel="canonical" href={URLS.appBase} />
      </head>
      <body>
        <Nav />
        <main>{children}</main>
        <Footer />
      </body>
    </html>
  );
}

function Nav() {
  return (
    <nav
      style={{
        position: "sticky",
        top: 0,
        zIndex: 100,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 2rem",
        height: "60px",
        background: "rgba(8,10,12,0.94)",
        backdropFilter: "blur(12px)",
        borderBottom: "1px solid var(--border)",
      }}
    >
      <a
        href="/"
        style={{
          fontFamily: "var(--font-head)",
          fontSize: "1.05rem",
          fontWeight: 800,
          color: "var(--white)",
          letterSpacing: "0.02em",
          textDecoration: "none",
        }}
      >
        Aletheia<span style={{ color: "var(--crimson-hi)" }}>Core</span>
      </a>
      <div
        style={{
          display: "flex",
          gap: "1.25rem",
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        <a
          href="/demo"
          style={{
            color: "var(--silver)",
            fontSize: "0.88rem",
            textDecoration: "none",
          }}
        >
          Demo
        </a>
        <a
          href={URLS.landingPage}
          style={{
            color: "var(--silver)",
            fontSize: "0.88rem",
            textDecoration: "none",
          }}
        >
          Docs
        </a>
        <a
          href={URLS.github}
          style={{
            color: "var(--silver)",
            fontSize: "0.88rem",
            textDecoration: "none",
          }}
          target="_blank"
          rel="noopener noreferrer"
        >
          GitHub
        </a>
        <a
          href="/#pricing"
          style={{
            color: "var(--silver)",
            fontSize: "0.88rem",
            textDecoration: "none",
          }}
        >
          Pricing
        </a>
        <a
          href="/#services"
          style={{
            color: "var(--silver)",
            fontSize: "0.88rem",
            textDecoration: "none",
          }}
        >
          Services
        </a>
        <a
          href="/demo"
          style={{
            background: "var(--crimson)",
            color: "var(--white)",
            padding: "0.38rem 0.95rem",
            borderRadius: "4px",
            fontSize: "0.84rem",
            fontWeight: 600,
            textDecoration: "none",
            transition: "background 0.2s",
          }}
        >
          Try Live Demo
        </a>
      </div>
    </nav>
  );
}

function Footer() {
  return (
    <footer
      style={{
        borderTop: "1px solid var(--border)",
        padding: "2.5rem 2rem",
        textAlign: "center",
      }}
    >
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          gap: "1.5rem",
          marginBottom: "1rem",
        }}
      >
        {[
          { label: "Demo", href: "/demo" },
          { label: "Docs", href: URLS.landingPage },
          { label: "Pricing", href: "/#pricing" },
          { label: "Services", href: "/#services" },
          { label: "GitHub", href: URLS.github },
          { label: `${URLS.contactEmail}`, href: `mailto:${URLS.contactEmail}` },
        ].map(({ label, href }) => (
          <a
            key={label}
            href={href}
            style={{
              color: "var(--muted)",
              fontSize: "0.85rem",
              textDecoration: "none",
            }}
          >
            {label}
          </a>
        ))}
      </div>
      <div style={{ color: "var(--muted)", fontSize: "0.82rem" }}>
        &copy; {PRODUCT.copyrightYear} {PRODUCT.copyrightHolder} &mdash;{" "}
        {PRODUCT.license} License &nbsp;|&nbsp; v{PRODUCT.version}
      </div>
    </footer>
  );
}
