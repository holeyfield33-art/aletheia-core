import type { Metadata } from "next";
import { Syne, JetBrains_Mono, Inter } from "next/font/google";
import { Analytics } from "@vercel/analytics/react";
import { SpeedInsights } from "@vercel/speed-insights/next";
import "./globals.css";
import { PRODUCT, URLS } from "@/lib/site-config";
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

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${syne.variable} ${jetbrainsMono.variable} ${inter.variable}`}>
      <head>
        <link rel="icon" href="/favicon.ico" />
        <link rel="canonical" href={URLS.appBase} />
        <style dangerouslySetInnerHTML={{ __html: `
          @keyframes constructionPulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
          }
          .construction-banner {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 9999;
            background: linear-gradient(90deg, #8B1A2A 0%, #B02236 50%, #8B1A2A 100%);
            color: #f0eee8;
            text-align: center;
            padding: 0.55rem 1rem;
            font-family: var(--font-mono), monospace;
            font-size: 0.78rem;
            letter-spacing: 0.06em;
            border-bottom: 2px solid #B02236;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.75rem;
          }
          .construction-banner .pulse-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #2eb87a;
            animation: constructionPulse 2s ease-in-out infinite;
          }
          body { padding-top: 38px !important; }
          nav[style] { top: 38px !important; }
        ` }} />
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem("aletheia-theme");if(!t)t=matchMedia("(prefers-color-scheme:light)").matches?"light":"dark";document.documentElement.setAttribute("data-theme",t)}catch(e){}})()`,
          }}
        />
      </head>
      <body>
        <div className="construction-banner">
          <span className="pulse-dot" />
          UNDER CONSTRUCTION — Full platform launch in progress. Demo is live.
          <span className="pulse-dot" />
        </div>
        <a
          href="#main-content"
          className="skip-link"
        >
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
          { label: "Blog", href: "/blog" },
          { label: "Changelog", href: "/changelog" },
          { label: "CLI", href: "/cli" },
          { label: "Docs", href: "/docs" },
          { label: "Pricing", href: "/pricing" },
          { label: "Services", href: "/#services" },
          { label: "Status", href: "/status" },
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
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          gap: "1.25rem",
          marginBottom: "1rem",
        }}
      >
        {[
          { label: "Privacy", href: "/legal/privacy" },
          { label: "Terms", href: "/legal/terms" },
          { label: "Security", href: "/legal/security" },
          { label: "Accessibility", href: "/legal/accessibility" },
        ].map(({ label, href }) => (
          <a
            key={label}
            href={href}
            style={{
              color: "var(--muted)",
              fontSize: "0.78rem",
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
