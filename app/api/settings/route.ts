import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import prisma from "@/lib/prisma";

export async function PATCH(request: Request) {
  const session = await getServerSession(authOptions);
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  let body: { name?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const name = typeof body.name === "string" ? body.name.trim().slice(0, 100) : undefined;
  if (name === undefined) {
    return NextResponse.json({ error: "No valid fields to update" }, { status: 400 });
  }

  await prisma.user.update({
    where: { id: session.user.id },
    data: { name: name || null },
  });

  return NextResponse.json({ ok: true });
}
