export default function DashboardLoading() {
  return (
    <div
      style={{
        minHeight: "60vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "0.88rem",
          color: "var(--muted)",
          letterSpacing: "0.05em",
        }}
      >
        Loading dashboard…
      </div>
    </div>
  );
}
