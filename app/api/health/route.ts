import { NextResponse } from "next/server";

/**
 * Health-check endpoint — reports which required env vars are set.
 * Visit /api/health on Vercel to diagnose configuration issues.
 */
export async function GET() {
  const required: Record<string, string | undefined> = {
    NEXTAUTH_SECRET: process.env.NEXTAUTH_SECRET,
    NEXTAUTH_URL: process.env.NEXTAUTH_URL,
    DATABASE_URL: process.env.DATABASE_URL,
  };

  const optional: Record<string, string | undefined> = {
    DIRECT_URL: process.env.DIRECT_URL,
    GITHUB_CLIENT_ID: process.env.GITHUB_CLIENT_ID,
    GITHUB_CLIENT_SECRET: process.env.GITHUB_CLIENT_SECRET,
    GOOGLE_CLIENT_ID: process.env.GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET: process.env.GOOGLE_CLIENT_SECRET,
  };

  const status: Record<string, string> = {};
  let allOk = true;

  for (const [key, val] of Object.entries(required)) {
    if (val) {
      status[key] = `SET (${val.slice(0, 4)}…)`;
    } else {
      status[key] = "MISSING ❌";
      allOk = false;
    }
  }

  for (const [key, val] of Object.entries(optional)) {
    status[key] = val ? `SET (${val.slice(0, 4)}…)` : "not set";
  }

  // Quick Prisma connectivity test
  let dbStatus = "untested";
  if (process.env.DATABASE_URL) {
    try {
      const { PrismaClient } = await import("@prisma/client");
      const prisma = new PrismaClient();
      await prisma.$queryRaw`SELECT 1`;
      await prisma.$disconnect();
      dbStatus = "connected ✅";
    } catch (e: unknown) {
      dbStatus = `error: ${e instanceof Error ? e.message.slice(0, 120) : String(e)}`;
    }
  }

  return NextResponse.json(
    { ok: allOk, env: status, database: dbStatus },
    { status: allOk ? 200 : 503 },
  );
}
