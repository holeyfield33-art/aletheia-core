import { NextResponse } from "next/server";

/**
 * Returns a bounded summary of the demo allowlist without disclosing the raw
 * host inventory. The UI only needs to know whether a policy exists.
 */

const corsHeaders: Record<string, string> = {
  "X-Content-Type-Options": "nosniff",
  "Cache-Control": "public, max-age=60",
};

function parseRequestOrigin(request: Request): string | null {
  const originHeader = request.headers.get("origin");
  if (originHeader) {
    try {
      return new URL(originHeader).origin;
    } catch {
      return null;
    }
  }

  const referer = request.headers.get("referer");
  if (referer) {
    try {
      return new URL(referer).origin;
    } catch {
      return null;
    }
  }

  return null;
}

export async function GET(request: Request) {
  const raw = process.env.ALETHEIA_DEMO_ORIGINS ?? "";
  const origins = raw
    .split(",")
    .map((o) => o.trim())
    .filter(Boolean);
  const source = parseRequestOrigin(request);

  return NextResponse.json(
    {
      allowlistConfigured: origins.length > 0,
      allowedOriginCount: origins.length,
      currentOriginAllowed: source ? origins.includes(source) : null,
    },
    { headers: corsHeaders },
  );
}
