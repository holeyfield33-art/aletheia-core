import type { Metadata } from "next";
import { Syne, JetBrains_Mono, Inter } from "next/font/google";
import "./globals.css";
import { PRODUCT, URLS } from "@/lib/site-config";
import AuthProvider from "@/app/components/AuthProvider";
import Nav from "@/app/components/Nav";
import { ToastProvider } from "@/app/components/Toast";

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
      </head>
      <body>
        <AuthProvider>
          <ToastProvider>
            <Nav />
            <main>{children}</main>
            <Footer />
          </ToastProvider>
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
