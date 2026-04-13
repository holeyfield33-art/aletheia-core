import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "404 — Page Not Found",
};

export default function NotFound() {
  return (
    <div
      style={{
        minHeight: "calc(100vh - 200px)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "2rem",
        textAlign: "center",
      }}
    >
      <div
        style={{
          fontSize: "clamp(4rem, 10vw, 7rem)",
          fontFamily: "var(--font-head)",
          fontWeight: 800,
          color: "var(--crimson)",
          lineHeight: 1,
          marginBottom: "1rem",
        }}
      >
        404
      </div>
      <h1
        style={{
          fontSize: "clamp(1.2rem, 3vw, 1.6rem)",
          fontFamily: "var(--font-head)",
          fontWeight: 700,
          color: "var(--white)",
          marginBottom: "0.75rem",
        }}
      >
        Page not found
      </h1>
      <p
        style={{
          color: "var(--muted)",
          fontSize: "0.95rem",
          maxWidth: "400px",
          marginBottom: "2rem",
          lineHeight: 1.6,
        }}
      >
        The page you&apos;re looking for doesn&apos;t exist or has been moved.
      </p>
      <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", justifyContent: "center" }}>
        <Link href="/" className="btn-primary">
          Go home
        </Link>
        <Link href="/dashboard" className="btn-secondary">
          Dashboard
        </Link>
      </div>
    </div>
  );
}
