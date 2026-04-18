import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import prisma from "@/lib/prisma";

export async function GET(request: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session?.user?.id) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const { searchParams } = request.nextUrl;
  const limit = Math.min(1000, Math.max(1, parseInt(searchParams.get("limit") ?? "1000", 10)));
  const cursor = searchParams.get("cursor"); // last id for cursor-based pagination

  const where: Record<string, unknown> = { userId: session.user.id };
  if (cursor) {
    where.id = { lt: cursor };
  }

  const logs = await prisma.auditLog.findMany({
    where,
    orderBy: { createdAt: "desc" },
    take: limit,
    select: {
      id: true,
      decision: true,
      action: true,
      origin: true,
      threatScore: true,
      policyHash: true,
      payloadHash: true,
      receipt: true,
      createdAt: true,
    },
  });

  const jsonl = logs
    .map((log) =>
      JSON.stringify({
        event_id: log.id,
        timestamp: log.createdAt.toISOString(),
        decision: log.decision,
        action: log.action,
        origin: log.origin,
        threat_score: log.threatScore,
        payload_sha256: log.payloadHash,
        receipt: log.receipt,
        policy_hash: log.policyHash,
      })
    )
    .join("\n");

  return new NextResponse(jsonl, {
    headers: {
      "Content-Type": "application/x-ndjson",
      "Content-Disposition": `attachment; filename="aletheia-evidence-${new Date().toISOString().slice(0, 10)}.jsonl"`,
    },
  });
}
