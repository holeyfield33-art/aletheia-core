import type { Metadata } from "next";
import { requireAuth } from "@/lib/server-auth";
import prisma from "@/lib/prisma";
import DashboardOverview from "./DashboardOverview";

export const metadata: Metadata = {
  title: "Dashboard",
};

export default async function DashboardIndex() {
  const session = await requireAuth();
  const userId = session.user.id;

  let keyCount = 0;
  let totalRequests = 0;
  let recentLogs = 0;

  try {
    // Sequential queries — avoids PgBouncer/Supavisor "prepared statement already exists" errors
    keyCount = await prisma.apiKey.count({ where: { userId, status: "active" } });
    const agg = await prisma.apiKey.aggregate({ where: { userId }, _sum: { requestsUsed: true } });
    totalRequests = agg._sum.requestsUsed ?? 0;
    recentLogs = await prisma.auditLog.count({ where: { userId } });
  } catch (err) {
    console.error("[Dashboard] Failed to load stats:", err);
  }

  return (
    <DashboardOverview
      keyCount={keyCount}
      totalRequests={totalRequests}
      logCount={recentLogs}
      plan={session.user.plan}
    />
  );
}
