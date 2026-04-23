import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import prisma from "@/lib/prisma";
import crypto from "crypto";
import { secureJson } from "@/lib/api-utils";

/**
 * Key management — user-scoped, session-protected.
 *
 * GET  /api/keys  → list current user's keys
 * POST /api/keys  → create a new trial key for current user
 */

const PLAN_QUOTAS: Record<string, number> = {
  trial: 1_000,
  pro: 100_000,
};

const MAX_KEYS_PER_USER = 10;

function hashKey(raw: string): string {
  const salt = process.env.ALETHEIA_KEY_SALT;
  if (!salt) {
    if (process.env.NODE_ENV === "production") {
      throw new Error("ALETHEIA_KEY_SALT must be set in production to securely hash API keys.");
    }
    // Dev/test only: warn loudly but allow unsalted hash
    console.warn("[keys] ALETHEIA_KEY_SALT is not set — API key hashes are unsalted (dev mode only)");
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

  return secureJson({ keys });
}

export async function POST(request: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session?.user?.id) {
    return secureJson({ error: "unauthorized" }, { status: 401 });
  }

  // Enforce key limit
  const existingCount = await prisma.apiKey.count({
    where: { userId: session.user.id, status: "active" },
  });
  if (existingCount >= MAX_KEYS_PER_USER) {
    return secureJson(
      { error: "limit_reached", message: `Maximum ${MAX_KEYS_PER_USER} active keys per account.` },
      { status: 429 },
    );
  }

  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return secureJson({ error: "invalid_json" }, { status: 400 });
  }

  const name = typeof body.name === "string" ? body.name.slice(0, 64).trim() : "Unnamed Key";
  const plan = "trial"; // users create trial keys; pro via billing upgrade

  const rawKey = `sk_${plan}_${crypto.randomBytes(24).toString("hex")}`;
  const keyHash = hashKey(rawKey);
  const keyPrefix = rawKey.slice(0, 12) + "..." + rawKey.slice(-4);
  const quota = PLAN_QUOTAS[plan] ?? 1000;

  const now = new Date();
  const periodStart = new Date(now.getFullYear(), now.getMonth(), 1);
  const periodEnd = new Date(now.getFullYear(), now.getMonth() + 1, 1);

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
    },
  });

  return secureJson(
    {
      key: rawKey, // returned exactly once
      id: record.id,
      name: record.name,
      keyPrefix: record.keyPrefix,
      plan: record.plan,
      status: record.status,
      monthlyQuota: record.monthlyQuota,
      requestsUsed: 0,
      periodStart: record.periodStart.toISOString(),
      periodEnd: record.periodEnd.toISOString(),
      createdAt: record.createdAt.toISOString(),
    },
    { status: 201 },
  );
}
