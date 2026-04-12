import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import prisma from "@/lib/prisma";

export async function GET() {
  const session = await getServerSession(authOptions);
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const logs = await prisma.auditLog.findMany({
    where: { userId: session.user.id },
    orderBy: { createdAt: "desc" },
    take: 10000,
    select: {
      id: true,
      decision: true,
      action: true,
      origin: true,
      threatLevel: true,
      policyVersion: true,
      payloadHash: true,
      receiptSignature: true,
      createdAt: true,
    },
  });

  const jsonl = logs
    .map((log: Record<string, unknown>) =>
      JSON.stringify({
        event_id: log.id,
        timestamp: log.createdAt.toISOString(),
        decision: log.decision,
        action: log.action,
        origin: log.origin,
        threat_level: log.threatLevel,
        payload_sha256: log.payloadHash,
        signature: log.receiptSignature,
        policy_version: log.policyVersion,
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
