"use client";

import { useSession } from "next-auth/react";
import { URLS } from "@/lib/site-config";

export default function Nav() {
  const { data: session, status } = useSession();
  const isAuthed = status === "authenticated";

  return (
    <nav
      style={{
        position: "sticky",
        top: 0,
        zIndex: 100,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 2rem",
        height: "60px",
        background: "rgba(8,10,12,0.94)",
        backdropFilter: "blur(12px)",
        borderBottom: "1px solid var(--border)",
      }}
    >
      <a
        href="/"
        style={{
          fontFamily: "var(--font-head)",
          fontSize: "1.05rem",
          fontWeight: 800,
          color: "var(--white)",
          letterSpacing: "0.02em",
          textDecoration: "none",
        }}
      >
        Aletheia<span style={{ color: "var(--crimson-hi)" }}>Core</span>
      </a>
      <div
        style={{
          display: "flex",
          gap: "1.25rem",
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        <a
          href="/demo"
          style={{
            color: "var(--silver)",
            fontSize: "0.88rem",
            textDecoration: "none",
          }}
        >
          Demo
        </a>
        <a
          href={URLS.landingPage}
          style={{
            color: "var(--silver)",
            fontSize: "0.88rem",
            textDecoration: "none",
          }}
        >
          Docs
        </a>
        <a
          href={URLS.github}
          style={{
            color: "var(--silver)",
            fontSize: "0.88rem",
            textDecoration: "none",
          }}
          target="_blank"
          rel="noopener noreferrer"
        >
          GitHub
        </a>
        <a
          href="/#pricing"
          style={{
            color: "var(--silver)",
            fontSize: "0.88rem",
            textDecoration: "none",
          }}
        >
          Pricing
        </a>
        {isAuthed ? (
          <a
            href="/dashboard"
            style={{
              background: "var(--crimson)",
              color: "var(--white)",
              padding: "0.38rem 0.95rem",
              borderRadius: "4px",
              fontSize: "0.84rem",
              fontWeight: 600,
              textDecoration: "none",
              transition: "background 0.2s",
            }}
          >
            Dashboard
          </a>
        ) : (
          <>
            <a
              href="/auth/login"
              style={{
                color: "var(--silver)",
                fontSize: "0.88rem",
                textDecoration: "none",
              }}
            >
              Sign In
            </a>
            <a
              href="/auth/register"
              style={{
                background: "var(--crimson)",
                color: "var(--white)",
                padding: "0.38rem 0.95rem",
                borderRadius: "4px",
                fontSize: "0.84rem",
                fontWeight: 600,
                textDecoration: "none",
                transition: "background 0.2s",
              }}
            >
              Get Started
            </a>
          </>
        )}
      </div>
    </nav>
  );
}
