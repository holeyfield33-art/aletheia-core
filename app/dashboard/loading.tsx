import { SkeletonStatCards, SkeletonTable } from "@/app/components/Skeleton";

export default function DashboardLoading() {
  return (
    <div>
      <div
        className="skeleton-text"
        style={{ width: "100px", marginBottom: "0.75rem" }}
      />
      <div
        className="skeleton"
        style={{ height: "1.5rem", width: "200px", marginBottom: "2rem" }}
      />
      <SkeletonStatCards count={4} />
      <div style={{ marginTop: "1.5rem" }}>
        <SkeletonTable rows={5} />
      </div>
    </div>
  );
}
