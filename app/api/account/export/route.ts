import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import prisma from "@/lib/prisma";
import { consumeRateLimit } from "@/lib/rate-limit";

const EXPORT_COOLDOWN_MS = 24 * 60 * 60 * 1000;

export async function POST() {
  const session = await getServerSession(authOptions);
  if (!session?.user?.id || !session?.user?.email) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  // Rate-limit BEFORE the heavy multi-relation query so spam requests don't
  // burn DB read budget.
  const rateLimit = await consumeRateLimit({
    action: "account_export",
    key: session.user.id,
    limit: 1,
    windowMs: EXPORT_COOLDOWN_MS,
  });
  if (!rateLimit.allowed) {
    return NextResponse.json(
      { error: "rate_limited", message: "You can export your data once every 24 hours." },
      { status: 429, headers: { "Retry-After": String(rateLimit.retryAfterSeconds) } },
    );
  }

  const user = await prisma.user.findUnique({
    where: { email: session.user.email },
    select: {
      id: true,
      name: true,
      email: true,
      emailVerified: true,
      image: true,
      role: true,
      plan: true,
      createdAt: true,
      updatedAt: true,
      tosAcceptedAt: true,
      stripeCustomerId: true,
      stripeSubscriptionId: true,
      stripePriceId: true,
      stripeCurrentPeriodEnd: true,
      apiKeys: {
        select: {
          id: true,
          name: true,
          keyPrefix: true,
          status: true,
          createdAt: true,
          lastUsedAt: true,
        },
      },
      auditLogs: {
        where: {
          createdAt: {
            gte: new Date(Date.now() - 90 * 24 * 60 * 60 * 1000), // 90 days
          },
        },
        select: {
          id: true,
          action: true,
          decision: true,
          origin: true,
          threatScore: true,
          createdAt: true,
        },
        orderBy: { createdAt: "desc" },
        take: 2000,
      },
    },
  });

  if (!user) {
    return NextResponse.json({ error: "not_found" }, { status: 404 });
  }

  const exportData = {
    exported_at: new Date().toISOString(),
    profile: {
      id: user.id,
      name: user.name,
      email: user.email,
      emailVerified: user.emailVerified,
      image: user.image,
      role: user.role,
      plan: user.plan,
      createdAt: user.createdAt,
      updatedAt: user.updatedAt,
      tosAcceptedAt: user.tosAcceptedAt,
    },
    billing: {
      stripeCustomerId: user.stripeCustomerId ? "****" + user.stripeCustomerId.slice(-4) : null,
      stripeSubscriptionId: user.stripeSubscriptionId ? "****" + user.stripeSubscriptionId.slice(-4) : null,
      stripePriceId: user.stripePriceId,
      stripeCurrentPeriodEnd: user.stripeCurrentPeriodEnd,
    },
    api_keys: user.apiKeys.map((k) => ({
      id: k.id,
      name: k.name,
      keyPrefix: k.keyPrefix,
      status: k.status,
      createdAt: k.createdAt,
      lastUsedAt: k.lastUsedAt,
    })),
    audit_logs: {
      retention_days: 90,
      count: user.auditLogs.length,
      truncated: user.auditLogs.length === 2000,
      receipt_export_path: "/dashboard/evidence",
      entries: user.auditLogs,
    },
  };

  return new NextResponse(JSON.stringify(exportData), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
      "Content-Disposition": `attachment; filename="aletheia-data-export-${new Date().toISOString().slice(0, 10)}.json"`,
      "Cache-Control": "no-store",
    },
  });
}
