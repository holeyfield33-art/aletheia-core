import type { Metadata } from "next";
import { requireAuth } from "@/lib/server-auth";
import prisma from "@/lib/prisma";
import { PRICING } from "@/lib/site-config";
import { getCurrentMonthUsage } from "@/lib/usage-tracking";
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
  let totalQuota = 0;
  let currentMonthUsage = 0;
  let estimatedPaygCost = 0;

  try {
    // Sequential queries — avoids PgBouncer/Supavisor "prepared statement already exists" errors
    keyCount = await prisma.apiKey.count({ where: { userId, status: "active" } });
    const agg = await prisma.apiKey.aggregate({ where: { userId }, _sum: { requestsUsed: true, monthlyQuota: true } });
    totalRequests = agg._sum.requestsUsed ?? 0;
    totalQuota = agg._sum.monthlyQuota ?? 0;
    recentLogs = await prisma.auditLog.count({ where: { userId } });
    if (session.user.plan === "ENTERPRISE") {
      currentMonthUsage = await getCurrentMonthUsage(userId);
      estimatedPaygCost = currentMonthUsage * PRICING.payg.pricePerReceipt;
    }
  } catch (err) {
    console.error("[Dashboard] Failed to load stats:", err);
  }

  return (
    <DashboardOverview
      keyCount={keyCount}
      totalRequests={totalRequests}
      logCount={recentLogs}
      plan={session.user.plan}
      isNewUser={keyCount === 0 && totalRequests === 0}
      totalQuota={totalQuota}
      currentMonthUsage={currentMonthUsage}
      estimatedPaygCost={estimatedPaygCost}
    />
  );
}
