"use client";

import { useState, Suspense } from "react";
import { signIn } from "next-auth/react";
import { useRouter, useSearchParams } from "next/navigation";

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const rawCallback = searchParams.get("callbackUrl") ?? "/dashboard";
  const oauthError = searchParams.get("error");
  const verified = searchParams.get("verified") === "true";
  // Prevent open redirect — only allow relative paths
  const callbackUrl =
    rawCallback.startsWith("/") && !rawCallback.startsWith("//")
      ? rawCallback
      : "/dashboard";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Show debug info on non-production builds (preview + dev)
  const isDebug =
    process.env.NODE_ENV === "development" ||
    process.env.NEXT_PUBLIC_VERCEL_ENV === "preview";

  const oauthMessages: Record<string, string> = {
    OAuthSignin: "Could not start OAuth sign-in. Check provider configuration.",
    OAuthCallback:
      "OAuth callback error. The redirect URI may not match the provider's allowed list.",
    OAuthCreateAccount: "Could not create account from OAuth provider.",
    OAuthAccountNotLinked:
      "This email is already linked to another sign-in method. Sign in with the original method first.",
    Callback: "OAuth callback error. Check server logs for details.",
    AccessDenied: "Access denied. You may not have permission to sign in.",
    Configuration:
      "Server configuration error. Check NEXTAUTH_URL and provider settings.",
    Default: "An authentication error occurred. Please try again.",
  };

  const handleCredentials = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const result = await signIn("credentials", {
      email,
      password,
      redirect: false,
    });

    setLoading(false);

    if (result?.error) {
      setError("Invalid email or password.");
      return;
    }

    router.push(callbackUrl);
    router.refresh();
  };

  const handleOAuth = (provider: string) => {
    signIn(provider, { callbackUrl });
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
          Sign In
        </h1>
        <p
          style={{
            color: "var(--muted)",
            fontSize: "0.85rem",
            marginBottom: "1.5rem",
          }}
        >
          Access your Aletheia Core dashboard
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
          </div>
        )}

        {oauthError && !error && (
          <div
            style={{
              background: "rgba(220,38,38,0.12)",
              border: "1px solid rgba(220,38,38,0.3)",
              color: "#f87171",
              padding: "0.75rem 1rem",
              fontSize: "0.82rem",
              marginBottom: "1rem",
            }}
          >
            {oauthMessages[oauthError] ?? oauthMessages.Default}
          </div>
        )}

        {verified && !error && (
          <div
            style={{
              background: "rgba(46,184,122,0.1)",
              border: "1px solid rgba(46,184,122,0.3)",
              color: "var(--green)",
              padding: "0.75rem 1rem",
              fontSize: "0.82rem",
              marginBottom: "1rem",
            }}
          >
            Email verified successfully. You can now sign in.
          </div>
        )}

        {isDebug && (
          <div
            style={{
              background: "rgba(59,130,246,0.08)",
              border: "1px solid rgba(59,130,246,0.25)",
              color: "#93c5fd",
              padding: "0.6rem 0.75rem",
              fontSize: "0.72rem",
              fontFamily: "var(--font-mono)",
              marginBottom: "1rem",
              lineHeight: 1.7,
              wordBreak: "break-all",
            }}
          >
            <div
              style={{
                fontWeight: 600,
                marginBottom: "0.25rem",
                color: "#60a5fa",
              }}
            >
              Debug (non-production only)
            </div>
            <div>callbackUrl: {callbackUrl}</div>
            <div>
              NEXT_PUBLIC_VERCEL_ENV:{" "}
              {process.env.NEXT_PUBLIC_VERCEL_ENV ?? "(unset)"}
            </div>
            <div>
              NEXT_PUBLIC_VERCEL_URL:{" "}
              {process.env.NEXT_PUBLIC_VERCEL_URL ?? "(unset)"}
            </div>
            {oauthError && <div>OAuth error code: {oauthError}</div>}
          </div>
        )}

        <form onSubmit={handleCredentials}>
          <label
            htmlFor="login-email"
            style={{
              display: "block",
              fontFamily: "var(--font-mono)",
              fontSize: "0.72rem",
              color: "var(--muted)",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              marginBottom: "0.35rem",
            }}
          >
            Email
          </label>
          <input
            id="login-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
            style={{
              width: "100%",
              padding: "0.6rem 0.75rem",
              background: "#09090b",
              border: "1px solid var(--border)",
              color: "var(--white)",
              fontFamily: "var(--font-mono)",
              fontSize: "0.85rem",
              marginBottom: "1rem",
              boxSizing: "border-box",
            }}
          />

          <label
            htmlFor="login-password"
            style={{
              display: "block",
              fontFamily: "var(--font-mono)",
              fontSize: "0.72rem",
              color: "var(--muted)",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              marginBottom: "0.35rem",
            }}
          >
            Password
          </label>
          <input
            id="login-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
            style={{
              width: "100%",
              padding: "0.6rem 0.75rem",
              background: "#09090b",
              border: "1px solid var(--border)",
              color: "var(--white)",
              fontFamily: "var(--font-mono)",
              fontSize: "0.85rem",
              marginBottom: "1.25rem",
              boxSizing: "border-box",
            }}
          />

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
            {loading ? "Signing in…" : "Sign In"}
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
          Don&apos;t have an account?{" "}
          <a
            href="/auth/register"
            style={{ color: "var(--crimson-hi)", textDecoration: "none" }}
          >
            Sign up
          </a>
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<LoginLoadingFallback />}>
      <LoginContent />
    </Suspense>
  );
}

function LoginLoadingFallback() {
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
          color: "var(--muted)",
          textAlign: "center",
        }}
      >
        Loading sign-in…
      </div>
    </div>
  );
}
