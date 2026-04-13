import { NextResponse } from "next/server";

/**
 * Returns the list of whitelisted demo origins so the UI can show
 * real-time trust status before the user clicks "Run Audit".
 *
 * Only exposes the demo-scoped allowlist — no security-sensitive data.
 */

const corsHeaders: Record<string, string> = {
  "X-Content-Type-Options": "nosniff",
  "Cache-Control": "public, max-age=60",
};

export async function GET() {
  const raw = process.env.ALETHEIA_DEMO_ORIGINS ?? "";
  const origins = raw
    .split(",")
    .map((o) => o.trim())
    .filter(Boolean);

  return NextResponse.json({ origins }, { headers: corsHeaders });
}
