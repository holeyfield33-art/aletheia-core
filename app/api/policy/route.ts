import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { readFile } from "fs/promises";
import path from "path";

export async function GET() {
  const session = await getServerSession(authOptions);
  if (!session?.user?.id) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  try {
    const policyPath = path.join(process.cwd(), "manifest", "security_policy.json");
    const raw = await readFile(policyPath, "utf-8");
    const policy = JSON.parse(raw);
    return NextResponse.json({ policy });
  } catch {
    return NextResponse.json({ error: "not_found" }, { status: 404 });
  }
}
