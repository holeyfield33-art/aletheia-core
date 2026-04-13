"use client";

export function SkeletonText({ width = "100%" }: { width?: string }) {
  return <div className="skeleton-text" style={{ width }} />;
}

export function SkeletonCard() {
  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "8px",
        padding: "1.25rem",
      }}
    >
      <SkeletonText width="40%" />
      <div className="skeleton" style={{ height: "2rem", width: "60%", marginTop: "0.5rem" }} />
    </div>
  );
}

export function SkeletonRow() {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr 1fr 0.5fr",
        gap: "1rem",
        padding: "0.75rem 0",
        borderBottom: "1px solid var(--border)",
      }}
    >
      <SkeletonText width="80%" />
      <SkeletonText width="50%" />
      <SkeletonText width="70%" />
      <SkeletonText width="40%" />
    </div>
  );
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div>
      {Array.from({ length: rows }).map((_, i) => (
        <SkeletonRow key={i} />
      ))}
    </div>
  );
}

export function SkeletonStatCards({ count = 4 }: { count?: number }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
        gap: "1rem",
      }}
    >
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}
