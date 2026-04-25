"use client";

import { useMemo, useState } from "react";
import { PRICING } from "@/lib/site-config";

function currency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: value < 1 ? 4 : 0,
    maximumFractionDigits: value < 1 ? 4 : 0,
  }).format(value);
}

export default function ROICalculator() {
  const [monthlyDecisions, setMonthlyDecisions] = useState(25000);

  const metrics = useMemo(() => {
    const paygCost = monthlyDecisions * PRICING.payg.pricePerReceipt;
    const scaleCost = PRICING.scale.price;
    const proCost = PRICING.pro.price;
    const scaleFit = monthlyDecisions <= PRICING.scale.receipts;
    const proFit = monthlyDecisions <= PRICING.pro.receipts;
    const recommendation = scaleFit
      ? "Scale"
      : proFit
        ? "Pro"
        : "PAYG";

    return {
      paygCost,
      scaleCost,
      proCost,
      recommendation,
      effectiveScale: scaleCost / monthlyDecisions,
      effectivePro: proCost / monthlyDecisions,
    };
  }, [monthlyDecisions]);

  return (
    <section
      style={{
        marginTop: "2rem",
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "10px",
        padding: "1.5rem",
      }}
    >
      <div style={{ marginBottom: "1rem" }}>
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "0.72rem",
            color: "var(--muted)",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            marginBottom: "0.4rem",
          }}
        >
          ROI Calculator
        </div>
        <h3
          style={{
            fontFamily: "var(--font-head)",
            fontSize: "1.2rem",
            color: "var(--white)",
            marginBottom: "0.4rem",
          }}
        >
          Estimate your cost per secured decision
        </h3>
        <p style={{ color: "var(--silver)", fontSize: "0.92rem", lineHeight: 1.6 }}>
          Slide your monthly decision volume to compare fixed-price tiers against PAYG.
        </p>
      </div>

      <label
        htmlFor="roi-range"
        style={{ display: "block", color: "var(--silver)", marginBottom: "0.75rem" }}
      >
        Monthly verified decisions: <strong style={{ color: "var(--white)" }}>{monthlyDecisions.toLocaleString()}</strong>
      </label>
      <input
        id="roi-range"
        type="range"
        min={1000}
        max={250000}
        step={1000}
        value={monthlyDecisions}
        onChange={(event) => setMonthlyDecisions(Number(event.target.value))}
        style={{ width: "100%", marginBottom: "1.25rem" }}
      />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: "0.9rem",
        }}
      >
        <MetricCard label="Scale" value={currency(metrics.scaleCost)} detail={`${currency(metrics.effectiveScale)} per secured decision`} />
        <MetricCard label="Pro" value={currency(metrics.proCost)} detail={`${currency(metrics.effectivePro)} per secured decision`} />
        <MetricCard label="PAYG" value={currency(metrics.paygCost)} detail={`${currency(PRICING.payg.pricePerReceipt)} per secured decision`} />
      </div>

      <div
        style={{
          marginTop: "1rem",
          padding: "0.9rem 1rem",
          borderRadius: "8px",
          background: "var(--surface-2)",
          color: "var(--silver)",
          lineHeight: 1.6,
        }}
      >
        Recommended launch tier: <strong style={{ color: "var(--white)" }}>{metrics.recommendation}</strong>
      </div>
    </section>
  );
}

function MetricCard({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div
      style={{
        border: "1px solid var(--border)",
        borderRadius: "8px",
        padding: "1rem",
        background: "var(--surface-2)",
      }}
    >
      <div
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "0.72rem",
          color: "var(--muted)",
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          marginBottom: "0.35rem",
        }}
      >
        {label}
      </div>
      <div style={{ fontFamily: "var(--font-head)", fontSize: "1.2rem", color: "var(--white)" }}>
        {value}
      </div>
      <div style={{ color: "var(--silver)", fontSize: "0.82rem", marginTop: "0.3rem" }}>
        {detail}
      </div>
    </div>
  );
}
