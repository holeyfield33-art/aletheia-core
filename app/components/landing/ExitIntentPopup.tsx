"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";

type ExitIntentPopupProps = {
  enabled?: boolean;
};

export default function ExitIntentPopup({ enabled = true }: ExitIntentPopupProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!enabled || dismissed) return;

    const handleMouseLeave = (e: MouseEvent) => {
      // Only trigger at the top of the page
      if ((e as any).clientY <= 0) {
        setIsVisible(true);
      }
    };

    // Also show after 30 seconds of inactivity
    timeoutRef.current = setTimeout(() => {
      if (!dismissed) {
        setIsVisible(true);
      }
    }, 30000);

    document.addEventListener("mouseleave", handleMouseLeave);

    return () => {
      document.removeEventListener("mouseleave", handleMouseLeave);
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [enabled, dismissed]);

  if (!isVisible || dismissed) return null;

  return (
    <div
      style={{
        position: "fixed",
        bottom: "2rem",
        right: "2rem",
        zIndex: 999,
        animation: "slideIn 0.3s ease-out",
      }}
    >
      <div
        style={{
          background: "linear-gradient(135deg, var(--crimson-glow) 0%, var(--surface) 100%)",
          border: "1px solid var(--crimson-hi)",
          borderRadius: "14px",
          padding: "1.5rem",
          maxWidth: "320px",
          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.5)",
        }}
      >
        <button
          type="button"
          onClick={() => setDismissed(true)}
          style={{
            position: "absolute",
            top: "0.75rem",
            right: "0.75rem",
            background: "none",
            border: "none",
            color: "var(--muted)",
            cursor: "pointer",
            fontSize: "1.2rem",
          }}
        >
          ✕
        </button>

        <h3
          style={{
            fontFamily: "var(--font-head)",
            fontSize: "1.1rem",
            color: "var(--white)",
            marginBottom: "0.5rem",
            paddingRight: "1.5rem",
          }}
        >
          1,000 Free Receipts
        </h3>

        <p style={{ color: "var(--silver)", fontSize: "0.9rem", lineHeight: 1.6, marginBottom: "1rem" }}>
          Get started with Aletheia. No card required.
        </p>

        <div style={{ display: "grid", gap: "0.6rem" }}>
          <Link className="btn-primary" href="/auth/register?callbackUrl=%2Fdashboard" style={{ textAlign: "center" }}>
            Get Your API Key
          </Link>
          <button
            type="button"
            onClick={() => setDismissed(true)}
            style={{
              background: "transparent",
              border: "1px solid var(--border)",
              color: "var(--silver)",
              borderRadius: "8px",
              padding: "0.6rem",
              cursor: "pointer",
              fontSize: "0.9rem",
            }}
          >
            Maybe Later
          </button>
        </div>
      </div>

      <style>{`
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateX(20px) translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateX(0) translateY(0);
          }
        }
      `}</style>
    </div>
  );
}
