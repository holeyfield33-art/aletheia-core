import { NextRequest } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import prisma from "@/lib/prisma";
import { secureJson } from "@/lib/api-utils";

/**
 * Per-key management — user-scoped, session-protected.
 *
 * GET    /api/keys/[id]  → get key usage (own keys only)
 * DELETE /api/keys/[id]  → revoke key (own keys only)
 */

function extractId(request: NextRequest): string | null {
  const parts = request.nextUrl.pathname.split("/");
  const id = parts[parts.length - 1];
  if (!id || id.length > 64 || !/^[a-zA-Z0-9_-]+$/.test(id)) return null;
  return id;
}

export async function GET(request: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session?.user?.id) {
    return secureJson({ error: "unauthorized" }, { status: 401 });
  }

  const id = extractId(request);
  if (!id) return secureJson({ error: "invalid_key_id" }, { status: 400 });

  const key = await prisma.apiKey.findFirst({
    where: { id, userId: session.user.id },
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

  if (!key) {
    return secureJson({ error: "key_not_found" }, { status: 404 });
  }

  return secureJson(key);
}

export async function DELETE(request: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session?.user?.id) {
    return secureJson({ error: "unauthorized" }, { status: 401 });
  }

  const id = extractId(request);
  if (!id) return secureJson({ error: "invalid_key_id" }, { status: 400 });

  // Only revoke own keys
  const key = await prisma.apiKey.findFirst({
    where: { id, userId: session.user.id },
  });

  if (!key) {
    return secureJson(
      { error: "key_not_found", message: "Key not found or already revoked." },
      { status: 404 },
    );
  }

  await prisma.apiKey.update({
    where: { id },
    data: { status: "revoked" },
  });

  return secureJson({ status: "revoked", id });
}
