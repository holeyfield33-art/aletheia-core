"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

type SuccessModalProps = {
  isVisible: boolean;
  onClose: () => void;
  receiptId?: string;
};

export default function SuccessModal({ isVisible, onClose, receiptId }: SuccessModalProps) {
  if (!isVisible) return null;

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100%",
        height: "100%",
        background: "rgba(0, 0, 0, 0.8)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        backdropFilter: "blur(4px)",
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border-hi)",
          borderRadius: "16px",
          padding: "2rem",
          maxWidth: "480px",
          textAlign: "center",
          animation: "slideUp 0.3s ease-out",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>✓</div>

        <h2
          style={{
            fontFamily: "var(--font-head)",
            fontSize: "1.6rem",
            color: "var(--white)",
            marginBottom: "0.5rem",
          }}
        >
          Decision Blocked & Signed
        </h2>

        <p style={{ color: "var(--silver)", lineHeight: 1.7, marginBottom: "1.5rem" }}>
          This unsafe action was blocked and recorded in a tamper-evident receipt. Ready to protect your agents?
        </p>

        {receiptId && (
          <div
            style={{
              background: "var(--surface-2)",
              border: "1px solid var(--border)",
              borderRadius: "10px",
              padding: "0.75rem",
              marginBottom: "1.5rem",
              fontFamily: "var(--font-mono)",
              fontSize: "0.8rem",
              color: "var(--muted)",
              wordBreak: "break-all",
            }}
          >
            Receipt: {receiptId}
          </div>
        )}

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "0.8rem",
          }}
        >
          <Link className="btn-secondary" href="/verify">
            Verify Receipt
          </Link>
          <Link className="btn-primary" href="/auth/register?callbackUrl=%2Fdashboard">
            Get Started
          </Link>
        </div>

        <button
          type="button"
          onClick={onClose}
          style={{
            background: "none",
            border: "none",
            color: "var(--muted)",
            cursor: "pointer",
            marginTop: "1rem",
            fontSize: "0.9rem",
            textDecoration: "underline",
          }}
        >
          Close
        </button>
      </div>

      <style>{`
        @keyframes slideUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  );
}
