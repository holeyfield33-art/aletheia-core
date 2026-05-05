import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { access, readFile } from "fs/promises";
import path from "path";

export async function GET() {
  const session = await getServerSession(authOptions);
  if (!session?.user?.id) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const policyPath = path.join(process.cwd(), "manifest", "security_policy.json");

  try {
    await access(policyPath);
  } catch {
    console.error(
      `[policy-route] manifest not bundled at ${policyPath}. cwd=${process.cwd()}`,
    );
    return NextResponse.json(
      { error: "not_found", hint: "manifest_not_bundled" },
      { status: 404 },
    );
  }

  try {
    const raw = await readFile(policyPath, "utf-8");
    const policy = JSON.parse(raw);
    return NextResponse.json({ policy });
  } catch (err) {
    console.error("[policy-route] read failed:", err);
    return NextResponse.json({ error: "read_failed" }, { status: 500 });
  }
}
