"use client";

import { useState, useEffect, useCallback } from "react";
import { useSession } from "next-auth/react";
import { URLS } from "@/lib/site-config";
import ThemeToggle from "@/app/components/ThemeToggle";

const linkStyle: React.CSSProperties = {
  color: "var(--silver)",
  fontSize: "0.88rem",
  textDecoration: "none",
};

const mobileLinkStyle: React.CSSProperties = {
  color: "var(--silver)",
  fontSize: "1rem",
  textDecoration: "none",
  padding: "0.75rem 0",
  borderBottom: "1px solid var(--border)",
  display: "block",
};

export default function Nav() {
  const { status } = useSession();
  const isAuthed = status === "authenticated";
  const [mobileOpen, setMobileOpen] = useState(false);

  // Close mobile drawer on Escape key
  const handleEscape = useCallback((e: KeyboardEvent) => {
    if (e.key === "Escape") setMobileOpen(false);
  }, []);

  useEffect(() => {
    if (mobileOpen) {
      document.addEventListener("keydown", handleEscape);
      return () => document.removeEventListener("keydown", handleEscape);
    }
  }, [mobileOpen, handleEscape]);

  const navLinks = [
    { label: "Demo", href: "/demo" },
    { label: "Blog", href: "/blog" },
    { label: "Changelog", href: "/changelog" },
    { label: "CLI", href: "/cli" },
    { label: "Docs", href: "/docs" },
    { label: "GitHub", href: URLS.github, external: true },
    { label: "Pricing", href: "/pricing" },
  ];

  return (
    <>
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
          background: "var(--surface)",
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

        {/* Desktop links */}
        <div
          className="nav-desktop"
          style={{
            display: "flex",
            gap: "1.25rem",
            alignItems: "center",
          }}
        >
          {navLinks.map(({ label, href, external }) => (
            <a
              key={label}
              href={href}
              style={linkStyle}
              {...(external
                ? { target: "_blank", rel: "noopener noreferrer" }
                : {})}
            >
              {label}
            </a>
          ))}
          <ThemeToggle />
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
              <a href="/auth/login" style={linkStyle}>
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
                Protect My Agent
              </a>
            </>
          )}
        </div>

        {/* Mobile hamburger */}
        <button
          className="nav-hamburger"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label={mobileOpen ? "Close menu" : "Open menu"}
          aria-expanded={mobileOpen}
          style={{
            display: "none",
            background: "none",
            border: "none",
            color: "var(--silver)",
            fontSize: "1.5rem",
            cursor: "pointer",
            padding: "0.25rem",
          }}
        >
          {mobileOpen ? "✕" : "☰"}
        </button>
      </nav>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div
          className="nav-mobile-drawer"
          role="dialog"
          aria-modal="true"
          aria-label="Navigation menu"
          style={{
            position: "fixed",
            top: "60px",
            left: 0,
            right: 0,
            bottom: 0,
            background: "var(--black)",
            zIndex: 99,
            padding: "1.5rem 2rem",
            overflowY: "auto",
          }}
        >
          {navLinks.map(({ label, href, external }) => (
            <a
              key={label}
              href={href}
              style={mobileLinkStyle}
              onClick={() => setMobileOpen(false)}
              {...(external
                ? { target: "_blank", rel: "noopener noreferrer" }
                : {})}
            >
              {label}
            </a>
          ))}
          <div
            style={{
              marginTop: "1.5rem",
              display: "flex",
              flexDirection: "column",
              gap: "0.75rem",
            }}
          >
            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <ThemeToggle />
            </div>
            {isAuthed ? (
              <a
                href="/dashboard"
                className="btn-primary"
                style={{ justifyContent: "center", textAlign: "center" }}
                onClick={() => setMobileOpen(false)}
              >
                Dashboard
              </a>
            ) : (
              <>
                <a
                  href="/auth/register"
                  className="btn-primary"
                  style={{ justifyContent: "center", textAlign: "center" }}
                  onClick={() => setMobileOpen(false)}
                >
                  Protect My Agent
                </a>
                <a
                  href="/auth/login"
                  className="btn-secondary"
                  style={{ justifyContent: "center", textAlign: "center" }}
                  onClick={() => setMobileOpen(false)}
                >
                  Sign In
                </a>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}
