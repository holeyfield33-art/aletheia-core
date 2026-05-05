// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems

import { NextRequest } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import prisma from "@/lib/prisma";
import { secureJson } from "@/lib/api-utils";

/**
 * GET /api/logs/:id
 * Returns a single audit log row including the full receipt JSON.
 * 404 when the row does not exist OR belongs to another user (no existence leak).
 */
export async function GET(
  _request: NextRequest,
  { params }: { params: { id: string } },
) {
  const session = await getServerSession(authOptions);
  if (!session?.user?.id) {
    return secureJson({ error: "unauthorized" }, { status: 401 });
  }

  const { id } = params;
  if (!id || typeof id !== "string") {
    return secureJson({ error: "not_found" }, { status: 404 });
  }

  const log = await prisma.auditLog.findFirst({
    where: { id, userId: session.user.id },
    select: {
      id: true,
      decision: true,
      action: true,
      origin: true,
      threatScore: true,
      reason: true,
      latencyMs: true,
      requestId: true,
      receipt: true,
      createdAt: true,
    },
  });

  if (!log) {
    return secureJson({ error: "not_found" }, { status: 404 });
  }

  return secureJson({ log });
}
