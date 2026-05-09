import { NextRequest } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import prisma from "@/lib/prisma";
import crypto from "crypto";
import { secureJson } from "@/lib/api-utils";
import { getHostedPlanConfig } from "@/lib/hosted-plans";

/**
 * Key management — user-scoped, session-protected.
 *
 * GET  /api/keys  → list current user's keys
 * POST /api/keys  → create a new trial key for current user
 */

function hashKey(raw: string): string {
  const salt = process.env.ALETHEIA_KEY_SALT;
  if (!salt) {
    if (process.env.NODE_ENV === "production") {
      throw new Error(
        "ALETHEIA_KEY_SALT must be set in production to securely hash API keys.",
      );
    }
    // Dev/test only: warn loudly but allow unsalted hash
    console.warn(
      "[keys] ALETHEIA_KEY_SALT is not set — API key hashes are unsalted (dev mode only)",
    );
    return crypto.createHash("sha256").update(raw).digest("hex");
  }
  return crypto.createHmac("sha256", salt).update(raw).digest("hex");
}

export async function GET() {
  const session = await getServerSession(authOptions);
  if (!session?.user?.id) {
    return secureJson({ error: "unauthorized" }, { status: 401 });
  }

  const keys = await prisma.apiKey.findMany({
    where: { userId: session.user.id },
    orderBy: { createdAt: "desc" },
    select: {
      id: true,
      name: true,
      keyPrefix: true,
      plan: true,
      status: true,
      monthlyQuota: true,
      requestsUsed: true,
      periodStart: true,
      periodEnd: true,
      createdAt: true,
      lastUsedAt: true,
    },
  });

  // Transform to snake_case to match frontend interface
  const transformedKeys = keys.map((k) => ({
    id: k.id,
    name: k.name,
    key_prefix: k.keyPrefix,
    plan: k.plan,
    status: k.status,
    monthly_quota: k.monthlyQuota,
    requests_used: k.requestsUsed,
    period_start: k.periodStart.toISOString(),
    period_end: k.periodEnd.toISOString(),
    created_at: k.createdAt.toISOString(),
    last_used_at: k.lastUsedAt ? k.lastUsedAt.toISOString() : null,
  }));

  return secureJson({ keys: transformedKeys });
}

export async function POST(request: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session?.user?.id) {
    return secureJson({ error: "unauthorized" }, { status: 401 });
  }

  // Enforce key limit
  const planConfig = getHostedPlanConfig(session.user.plan);
  const existingCount = await prisma.apiKey.count({
    where: { userId: session.user.id, status: "active" },
  });
  if (existingCount >= planConfig.maxActiveKeys) {
    return secureJson(
      {
        error: "limit_reached",
        message: `Maximum ${planConfig.maxActiveKeys} active keys per account.`,
      },
      { status: 429 },
    );
  }

  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return secureJson({ error: "invalid_json" }, { status: 400 });
  }

  const name =
    typeof body.name === "string"
      ? body.name.slice(0, 64).trim()
      : "Unnamed Key";
  const plan = planConfig.apiKeyPlan;

  const rawKey = `sk_${plan}_${crypto.randomBytes(24).toString("hex")}`;
  let keyHash: string;
  try {
    keyHash = hashKey(rawKey);
  } catch {
    return secureJson(
      {
        error: "configuration_error",
        message: "Key generation is temporarily unavailable. Contact support.",
      },
      { status: 503 },
    );
  }
  const keyPrefix = rawKey.slice(0, 12) + "..." + rawKey.slice(-4);
  const quota = planConfig.monthlyCalls;

  // Calculate period boundaries in UTC
  const now = new Date();
  const year = now.getUTCFullYear();
  const month = now.getUTCMonth();

  // Period start: first day of current month at 00:00:00 UTC
  const periodStart = new Date(Date.UTC(year, month, 1, 0, 0, 0, 0));
  // Period end: first day of next month at 00:00:00 UTC
  const periodEnd = new Date(Date.UTC(year, month + 1, 1, 0, 0, 0, 0));

  const record = await prisma.apiKey.create({
    data: {
      userId: session.user.id,
      name,
      keyHash,
      keyPrefix,
      plan,
      status: "active",
      monthlyQuota: quota,
      requestsUsed: 0,
      periodStart,
      periodEnd,
      createdAt: now,
    },
  });

  // Transform to snake_case for consistency with frontend
  return secureJson(
    {
      key: rawKey, // returned exactly once
      id: record.id,
      name: record.name,
      key_prefix: record.keyPrefix,
      plan: record.plan,
      status: record.status,
      monthly_quota: record.monthlyQuota,
      requests_used: 0,
      period_start: record.periodStart.toISOString(),
      period_end: record.periodEnd.toISOString(),
      created_at: record.createdAt.toISOString(),
    },
    { status: 201 },
  );
}
