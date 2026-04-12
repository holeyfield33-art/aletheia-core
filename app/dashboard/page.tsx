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

  // Sequential queries — avoids PgBouncer/Supavisor "prepared statement already exists" errors
  const keyCount = await prisma.apiKey.count({ where: { userId, status: "active" } });
  const totalRequests = await prisma.apiKey.aggregate({ where: { userId }, _sum: { requestsUsed: true } });
  const recentLogs = await prisma.auditLog.count({ where: { userId } });

  return (
    <DashboardOverview
      keyCount={keyCount}
      totalRequests={totalRequests._sum.requestsUsed ?? 0}
      logCount={recentLogs}
      plan={session.user.plan}
    />
  );
}
