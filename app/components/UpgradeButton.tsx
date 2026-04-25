"use client";

import { useState } from "react";

export default function UpgradeButton({
  label = "Upgrade Hosted Plan",
  className = "btn-primary",
  style,
  tier,
  plan = "PRO",
}: {
  label?: string;
  className?: string;
  style?: React.CSSProperties;
  tier?: "scale" | "pro" | "payg";
  plan?: "PRO" | "MAX";
}) {
  const [loading, setLoading] = useState(false);

  async function handleClick() {
    if (loading) return;
    setLoading(true);
    const requestedTier = tier ?? (plan === "MAX" ? "pro" : "scale");
    try {
      const res = await fetch(`/api/stripe/checkout?tier=${requestedTier}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tier: requestedTier }),
      });
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
