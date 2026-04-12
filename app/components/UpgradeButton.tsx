"use client";

import { useState } from "react";

export default function UpgradeButton({
  label = "Upgrade to Hosted Pro",
  className = "btn-primary",
  style,
}: {
  label?: string;
  className?: string;
  style?: React.CSSProperties;
}) {
  const [loading, setLoading] = useState(false);

  async function handleClick() {
    if (loading) return;
    setLoading(true);
    try {
      const res = await fetch("/api/stripe/checkout", { method: "POST" });
      const data = await res.json();
      if (data.url) {
        window.location.href = data.url;
      } else {
        alert(data.error || "Unable to start checkout. Please try again.");
      }
    } catch {
      alert("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <button
      onClick={handleClick}
      disabled={loading}
      className={className}
      style={{
        cursor: loading ? "not-allowed" : "pointer",
        opacity: loading ? 0.7 : 1,
        ...style,
      }}
    >
      {loading ? "Redirecting…" : label}
    </button>
  );
}
