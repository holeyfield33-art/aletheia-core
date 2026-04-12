"use client";

import { useSearchParams } from "next/navigation";

export default function AuthErrorPage() {
  const searchParams = useSearchParams();
  const error = searchParams.get("error");

  const messages: Record<string, string> = {
    Configuration: "Server configuration error. Please contact support.",
    AccessDenied: "Access denied. You may not have permission to sign in.",
    Verification: "Email verification link has expired. Please request a new one.",
    Default: "An authentication error occurred. Please try again.",
  };

  const message = messages[error ?? ""] ?? messages.Default;

  return (
    <div
      style={{
        minHeight: "calc(100vh - 60px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "2rem",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "400px",
          background: "var(--surface)",
          border: "1px solid var(--border)",
          padding: "2.5rem 2rem",
          textAlign: "center",
        }}
      >
        <h1
          style={{
            fontFamily: "var(--font-head)",
            fontSize: "1.5rem",
            fontWeight: 800,
            color: "#f87171",
            marginBottom: "1rem",
          }}
        >
          Authentication Error
        </h1>
        <p style={{ color: "var(--silver)", fontSize: "0.88rem", marginBottom: "1.5rem" }}>
          {message}
        </p>
        <a
          href="/auth/login"
          style={{
            display: "inline-block",
            padding: "0.6rem 1.5rem",
            background: "var(--crimson)",
            color: "var(--white)",
            fontWeight: 600,
            fontSize: "0.85rem",
            textDecoration: "none",
          }}
        >
          Back to Sign In
        </a>
      </div>
    </div>
  );
}
