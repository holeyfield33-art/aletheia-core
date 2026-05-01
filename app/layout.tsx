import type { Metadata } from "next";
import { headers } from "next/headers";
import Link from "next/link";
import { Syne, JetBrains_Mono, Inter } from "next/font/google";
import Script from "next/script";
import { Analytics } from "@vercel/analytics/react";
import { SpeedInsights } from "@vercel/speed-insights/next";
import "./globals.css";
import { PRODUCT, STATUS, URLS, SEO_SOLUTIONS } from "@/lib/site-config";
import AuthProvider from "@/app/components/AuthProvider";
import Nav from "@/app/components/Nav";
import { ToastProvider } from "@/app/components/Toast";
import { ThemeProvider } from "@/app/components/ThemeToggle";

const syne = Syne({
  subsets: ["latin"],
  weight: ["700", "800"],
  variable: "--font-head",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
  display: "swap",
});

const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-body",
  display: "swap",
});

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

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const headerStore = await headers();
  const nonce = headerStore.get("x-csp-nonce") ?? undefined;

  return (
    <html
      lang="en"
      className={`${syne.variable} ${jetbrainsMono.variable} ${inter.variable}`}
    >
      <head>
        <link rel="icon" href="/favicon.ico" />
        <link rel="canonical" href={URLS.appBase} />
        <Script
          src="/theme-bootstrap.js"
          strategy="beforeInteractive"
          nonce={nonce}
        />
      </head>
      <body>
        {STATUS.hostedApi !== "live" && (
          <div className="construction-banner">
            <span className="construction-banner-pulse" />
            UNDER CONSTRUCTION — Full platform launch in progress. Demo is live.
            <span className="construction-banner-pulse" />
          </div>
        )}
        <a href="#main-content" className="skip-link">
          Skip to main content
        </a>
        <AuthProvider>
          <ThemeProvider>
            <ToastProvider>
              <Nav />
              <main id="main-content">{children}</main>
              <Footer />
            </ToastProvider>
          </ThemeProvider>
          <Analytics />
          <SpeedInsights />
        </AuthProvider>
      </body>
    </html>
  );
}

function Footer() {
  const productLinks = [
    { label: "Demo", href: "/demo" },
    { label: "Blog", href: "/blog" },
    { label: "Changelog", href: "/changelog" },
    { label: "CLI", href: "/cli" },
    { label: "Docs", href: "/docs" },
    { label: "Pricing", href: "/pricing" },
    { label: "Services", href: "/#services" },
    { label: "Status", href: "/status" },
  ];

  const legalLinks = [
    { label: "Privacy", href: "/legal/privacy" },
    { label: "Terms", href: "/legal/terms" },
    { label: "Security", href: "/legal/security" },
    { label: "Accessibility", href: "/legal/accessibility" },
  ];

  return (
    <footer
      style={{
        borderTop: "1px solid var(--border)",
        padding: "2.5rem 2rem",
        textAlign: "left",
      }}
    >
      <div
        className="footer-columns"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
          gap: "1.5rem",
          marginBottom: "1rem",
          maxWidth: "980px",
          margin: "0 auto 1rem",
        }}
      >
        <div className="footer-col" style={{ display: "grid", gap: "0.45rem" }}>
          <h3
            style={{
              fontFamily: "var(--font-mono)",
              color: "var(--white)",
              fontSize: "0.82rem",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            Product
          </h3>
          {productLinks.map((link) => (
            <Link
              key={link.label}
              href={link.href}
              style={{ color: "var(--muted)", fontSize: "0.88rem", textDecoration: "none" }}
            >
              {link.label}
            </Link>
          ))}
        </div>

        <div className="footer-col" style={{ display: "grid", gap: "0.45rem" }}>
          <h3
            style={{
              fontFamily: "var(--font-mono)",
              color: "var(--white)",
              fontSize: "0.82rem",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            Solutions
          </h3>
          {SEO_SOLUTIONS.map((entry) => (
            <Link
              key={entry.href}
              href={entry.href}
              style={{ color: "var(--muted)", fontSize: "0.88rem", textDecoration: "none" }}
            >
              {entry.title}
            </Link>
          ))}
        </div>

        <div className="footer-col" style={{ display: "grid", gap: "0.45rem" }}>
          <h3
            style={{
              fontFamily: "var(--font-mono)",
              color: "var(--white)",
              fontSize: "0.82rem",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            Legal
          </h3>
          {legalLinks.map((link) => (
            <Link
              key={link.label}
              href={link.href}
              style={{ color: "var(--muted)", fontSize: "0.88rem", textDecoration: "none" }}
            >
              {link.label}
            </Link>
          ))}
          <a
            href={URLS.github}
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: "var(--muted)", fontSize: "0.88rem", textDecoration: "none" }}
          >
            GitHub
          </a>
          <a
            href={`mailto:${URLS.contactEmail}`}
            style={{ color: "var(--muted)", fontSize: "0.88rem", textDecoration: "none" }}
          >
            {URLS.contactEmail}
          </a>
        </div>
      </div>
      <div
        style={{
          color: "var(--muted)",
          fontSize: "0.82rem",
          textAlign: "center",
        }}
      >
        &copy; {PRODUCT.copyrightYear} {PRODUCT.copyrightHolder} &mdash;{" "}
        {PRODUCT.license} License &nbsp;|&nbsp; v{PRODUCT.version}
      </div>
    </footer>
  );
}
