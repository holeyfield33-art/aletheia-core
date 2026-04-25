import { NextRequest } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import prisma from "@/lib/prisma";
import { secureJson } from "@/lib/api-utils";

/**
 * Audit logs API — user-scoped, session-protected.
 *
 * GET /api/logs?page=1&limit=50&decision=DENIED&action=Transfer_Funds
 */

export async function GET(request: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session?.user?.id) {
    return secureJson({ error: "unauthorized" }, { status: 401 });
  }

  const { searchParams } = request.nextUrl;
  const page = Math.max(1, parseInt(searchParams.get("page") ?? "1", 10));
  const limit = Math.min(100, Math.max(1, parseInt(searchParams.get("limit") ?? "50", 10)));
  const decision = searchParams.get("decision");
  const action = searchParams.get("action");

  // Validate filter values to prevent query manipulation
  const validDecisions = ["PROCEED", "DENIED", "SANDBOX_BLOCKED", "RATE_LIMITED"];
  if (decision && !validDecisions.includes(decision)) {
    return secureJson({ error: "invalid_decision" }, { status: 400 });
  }
  // Sanitize action: alphanumeric + underscores only, max 64 chars
  if (action && (!/^[A-Za-z0-9_]{1,64}$/.test(action))) {
    return secureJson({ error: "invalid_action" }, { status: 400 });
  }

  const where: Record<string, unknown> = { userId: session.user.id };
  if (decision) where.decision = decision;
  if (action) where.action = action;

  // Sequential queries — avoids PgBouncer/Supavisor prepared statement collisions
  const logs = await prisma.auditLog.findMany({
    where,
    orderBy: { createdAt: "desc" },
    skip: (page - 1) * limit,
    take: limit,
    select: {
      id: true,
      decision: true,
      threatScore: true,
      action: true,
      origin: true,
      reason: true,
      latencyMs: true,
      requestId: true,
      createdAt: true,
    },
  });
  const total = await prisma.auditLog.count({ where });

  return secureJson({
    logs,
    pagination: {
      page,
      limit,
      total,
      pages: Math.ceil(total / limit),
    },
  });
}
