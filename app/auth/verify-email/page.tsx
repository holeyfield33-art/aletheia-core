import type { Metadata } from "next";
import { PRODUCT } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "Verify Your Email",
  description: `Check your inbox to verify your ${PRODUCT.name} account.`,
};

export default function VerifyEmailPage() {
  return (
    <div
      style={{
        maxWidth: "440px",
        margin: "0 auto",
        padding: "5rem 2rem 4rem",
        textAlign: "center",
      }}
    >
      <div
        style={{
          width: "56px",
          height: "56px",
          margin: "0 auto 1.5rem",
          borderRadius: "50%",
          background: "var(--crimson-glow)",
          border: "1px solid var(--crimson)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "1.5rem",
        }}
      >
        ✉
      </div>
      <h1
        style={{
          fontFamily: "var(--font-head)",
          fontSize: "1.5rem",
          fontWeight: 800,
          color: "var(--white)",
          marginBottom: "0.75rem",
        }}
      >
        Check your inbox
      </h1>
      <p
        style={{
          color: "var(--silver)",
          fontSize: "0.95rem",
          lineHeight: 1.65,
          marginBottom: "2rem",
        }}
      >
        We sent a verification link to your email address. Click the link to
        activate your account and sign in.
      </p>
      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "8px",
          padding: "1.25rem",
          marginBottom: "2rem",
        }}
      >
        <p
          style={{
            color: "var(--muted)",
            fontSize: "0.85rem",
            lineHeight: 1.6,
            margin: 0,
          }}
        >
          The link expires in 24 hours. Check your spam folder if you don&apos;t
          see it. If you still can&apos;t find it, try registering again.
        </p>
      </div>
      <a
        href="/auth/login"
        className="btn-secondary"
        style={{ textDecoration: "none" }}
      >
        Back to Sign In
      </a>
    </div>
  );
}
