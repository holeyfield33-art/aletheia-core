"use client";

import { useState } from "react";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";

export default function RegisterPage() {
  const router = useRouter();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [errorIsEmailTaken, setErrorIsEmailTaken] = useState(false);
  const [loading, setLoading] = useState(false);
  const [tosAccepted, setTosAccepted] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setErrorIsEmailTaken(false);

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (!tosAccepted) {
      setError("You must agree to the Terms of Service and Privacy Policy.");
      return;
    }

    setLoading(true);

    try {
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password, tosAccepted }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.message || "Registration failed.");
        setErrorIsEmailTaken(data.error === "registration_failed");
        setLoading(false);
        return;
      }

      // Redirect to verify-email page
      router.push("/auth/verify-email");
    } catch {
      setError("An unexpected error occurred.");
      setLoading(false);
    }
  };

  const handleOAuth = (provider: string) => {
    signIn(provider, { callbackUrl: "/dashboard" });
  };

  const inputStyle: React.CSSProperties = {
    width: "100%",
    padding: "0.6rem 0.75rem",
    background: "#09090b",
    border: "1px solid var(--border)",
    color: "var(--white)",
    fontFamily: "var(--font-mono)",
    fontSize: "0.85rem",
    marginBottom: "1rem",
    boxSizing: "border-box",
  };

  const labelStyle: React.CSSProperties = {
    display: "block",
    fontFamily: "var(--font-mono)",
    fontSize: "0.72rem",
    color: "var(--muted)",
    letterSpacing: "0.08em",
    textTransform: "uppercase",
    marginBottom: "0.35rem",
  };

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
        }}
      >
        <h1
          style={{
            fontFamily: "var(--font-head)",
            fontSize: "1.5rem",
            fontWeight: 800,
            color: "var(--white)",
            marginBottom: "0.5rem",
          }}
        >
          Create Account
        </h1>
        <p
          style={{
            color: "var(--muted)",
            fontSize: "0.85rem",
            marginBottom: "1.5rem",
          }}
        >
          Start free — 1,000 Sovereign Audit Receipts/month
        </p>

        {error && (
          <div
            role="alert"
            style={{
              background: "rgba(220,38,38,0.12)",
              border: "1px solid rgba(220,38,38,0.3)",
              color: "#f87171",
              padding: "0.75rem 1rem",
              fontSize: "0.82rem",
              marginBottom: "1rem",
            }}
          >
            {error}
            {errorIsEmailTaken && (
              <div style={{ marginTop: "0.5rem" }}>
                <a
                  href="/auth/login"
                  style={{
                    color: "#f87171",
                    textDecoration: "underline",
                    fontWeight: 600,
                  }}
                >
                  Go to Sign In &rarr;
                </a>
              </div>
            )}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <label htmlFor="reg-name" style={labelStyle}>
            Name
          </label>
          <input
            id="reg-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoComplete="name"
            maxLength={64}
            style={inputStyle}
          />

          <label htmlFor="reg-email" style={labelStyle}>
            Email
          </label>
          <input
            id="reg-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
            style={inputStyle}
          />

          <label htmlFor="reg-password" style={labelStyle}>
            Password
          </label>
          <input
            id="reg-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            maxLength={128}
            autoComplete="new-password"
            style={inputStyle}
          />

          <label htmlFor="reg-confirm" style={labelStyle}>
            Confirm Password
          </label>
          <input
            id="reg-confirm"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            autoComplete="new-password"
            style={inputStyle}
          />

          <label
            style={{
              display: "flex",
              alignItems: "flex-start",
              gap: "0.5rem",
              fontSize: "0.8rem",
              color: "var(--silver)",
              marginBottom: "1.25rem",
              cursor: "pointer",
              lineHeight: 1.5,
            }}
          >
            <input
              type="checkbox"
              checked={tosAccepted}
              onChange={(e) => setTosAccepted(e.target.checked)}
              style={{ marginTop: "0.2rem", accentColor: "var(--crimson)" }}
            />
            <span>
              I agree to the{" "}
              <a
                href="/legal/terms"
                target="_blank"
                style={{
                  color: "var(--crimson-hi)",
                  textDecoration: "underline",
                }}
              >
                Terms of Service
              </a>{" "}
              and{" "}
              <a
                href="/legal/privacy"
                target="_blank"
                style={{
                  color: "var(--crimson-hi)",
                  textDecoration: "underline",
                }}
              >
                Privacy Policy
              </a>
            </span>
          </label>

          <button
            type="submit"
            disabled={loading}
            style={{
              width: "100%",
              padding: "0.7rem",
              background: "var(--crimson)",
              color: "var(--white)",
              fontWeight: 600,
              fontSize: "0.88rem",
              border: "none",
              cursor: loading ? "not-allowed" : "pointer",
              opacity: loading ? 0.6 : 1,
              marginBottom: "1rem",
            }}
          >
            {loading ? "Creating account…" : "Create Account"}
          </button>
        </form>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.75rem",
            margin: "1.25rem 0",
          }}
        >
          <div
            style={{ flex: 1, height: "1px", background: "var(--border)" }}
          />
          <span style={{ color: "var(--muted)", fontSize: "0.75rem" }}>
            or continue with
          </span>
          <div
            style={{ flex: 1, height: "1px", background: "var(--border)" }}
          />
        </div>

        <div style={{ display: "flex", gap: "0.75rem" }}>
          <button
            type="button"
            onClick={() => handleOAuth("github")}
            style={{
              flex: 1,
              padding: "0.6rem",
              background: "#09090b",
              border: "1px solid var(--border)",
              color: "var(--silver)",
              fontSize: "0.82rem",
              cursor: "pointer",
            }}
          >
            GitHub
          </button>
          <button
            type="button"
            onClick={() => handleOAuth("google")}
            style={{
              flex: 1,
              padding: "0.6rem",
              background: "#09090b",
              border: "1px solid var(--border)",
              color: "var(--silver)",
              fontSize: "0.82rem",
              cursor: "pointer",
            }}
          >
            Google
          </button>
        </div>

        <p
          style={{
            textAlign: "center",
            marginTop: "1.5rem",
            fontSize: "0.82rem",
            color: "var(--muted)",
          }}
        >
          Already have an account?{" "}
          <a
            href="/auth/login"
            style={{ color: "var(--crimson-hi)", textDecoration: "none" }}
          >
            Sign in
          </a>
        </p>
      </div>
    </div>
  );
}
