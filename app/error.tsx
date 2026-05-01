"use client";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  void error;
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
          maxWidth: "440px",
          textAlign: "center",
        }}
      >
        <h1
          style={{
            fontFamily: "var(--font-head)",
            fontSize: "1.5rem",
            fontWeight: 800,
            color: "var(--white)",
            marginBottom: "0.75rem",
          }}
        >
          Something went wrong
        </h1>
        <p
          style={{
            color: "var(--muted)",
            fontSize: "0.88rem",
            marginBottom: "1.5rem",
            lineHeight: 1.6,
          }}
        >
          An unexpected error occurred. This is usually temporary.
        </p>
        <div
          style={{ display: "flex", gap: "0.75rem", justifyContent: "center" }}
        >
          <button
            onClick={reset}
            className="btn-primary"
            style={{ fontSize: "0.88rem", cursor: "pointer" }}
          >
            Try again
          </button>
          <a
            href="/"
            className="btn-secondary"
            style={{ fontSize: "0.88rem", textDecoration: "none" }}
          >
            Go home
          </a>
        </div>
      </div>
    </div>
  );
}
