"use client";

import React from "react";

type State = { hasError: boolean };

export class DemoErrorBoundary extends React.Component<
  { children: React.ReactNode },
  State
> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("[DemoErrorBoundary]", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            maxWidth: "600px",
            margin: "4rem auto",
            padding: "2rem",
            background: "var(--surface)",
            border: "1px solid var(--crimson-hi)",
            borderRadius: "10px",
            textAlign: "center",
          }}
        >
          <h2
            style={{
              fontFamily: "var(--font-head)",
              color: "var(--white)",
              fontSize: "1.25rem",
              marginBottom: "0.75rem",
            }}
          >
            Demo temporarily unavailable
          </h2>
          <p
            style={{
              color: "var(--silver)",
              fontSize: "0.9rem",
              marginBottom: "1.25rem",
            }}
          >
            Something went wrong. Please refresh and try again.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="btn-primary"
            style={{ fontSize: "0.88rem" }}
          >
            Refresh page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
