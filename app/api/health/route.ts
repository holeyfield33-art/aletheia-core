import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import prisma from "@/lib/prisma";

/**
 * Health-check endpoint — reports which required env vars are set.
 * Requires admin authentication in production.
 * In development, accessible without auth for local debugging.
 */
export async function GET(request: NextRequest) {
  // In production, require admin auth
  if (process.env.NODE_ENV === "production") {
    const session = await getServerSession(authOptions);
    if (!session?.user?.id || session.user.role !== "ADMIN") {
      return NextResponse.json({ error: "forbidden" }, { status: 403 });
    }
  }

  const requiredKeys = ["NEXTAUTH_SECRET", "DATABASE_URL"];
  const optionalKeys = [
    "NEXTAUTH_URL",
    "DIRECT_URL",
    "GITHUB_CLIENT_ID",
    "GITHUB_CLIENT_SECRET",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
  ];

  const status: Record<string, string> = {};
  let allOk = true;

  // Only report SET/MISSING — never leak partial values
  for (const key of requiredKeys) {
    if (process.env[key]) {
      status[key] = "SET";
    } else {
      status[key] = "MISSING";
      allOk = false;
    }
  }

  for (const key of optionalKeys) {
    status[key] = process.env[key] ? "SET" : "not set";
  }

  // Quick Prisma connectivity test using the shared singleton —
  // do NOT instantiate a new PrismaClient per request (connection leak).
  let dbStatus = "untested";
  if (process.env.DATABASE_URL) {
    try {
      await prisma.$queryRaw`SELECT 1`;
      dbStatus = "connected";
    } catch {
      dbStatus = "error";
    }
  }

  return NextResponse.json(
    { ok: allOk, env: status, database: dbStatus },
    { status: allOk ? 200 : 503 },
  );
}
