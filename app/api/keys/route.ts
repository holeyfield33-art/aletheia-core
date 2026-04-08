import { NextRequest, NextResponse } from "next/server";

/**
 * Key management proxy — keeps ALETHEIA_ADMIN_KEY server-side only.
 *
 * GET  /api/keys  → list all keys
 * POST /api/keys  → create a new trial key
 */

const BACKEND_BASE = (process.env.ALETHEIA_BACKEND_URL ?? "").replace(/\/+$/, "");
const ADMIN_KEY = process.env.ALETHEIA_ADMIN_KEY ?? "";
const TIMEOUT_MS = 5_000;

const securityHeaders: Record<string, string> = {
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "Cache-Control": "no-store",
};

function secureJson(body: unknown, init?: { status?: number }) {
  return NextResponse.json(body, {
    status: init?.status ?? 200,
    headers: securityHeaders,
  });
}

export async function GET() {
  if (!BACKEND_BASE || !ADMIN_KEY) {
    return secureJson(
      { keys: [], message: "Key management not configured on this instance." },
      { status: 200 },
    );
  }

  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
    const res = await fetch(`${BACKEND_BASE}/v1/keys`, {
      method: "GET",
      headers: { "X-Admin-Key": ADMIN_KEY },
      signal: ctrl.signal,
    });
    clearTimeout(timer);
    const data = await res.json();
    return secureJson(data, { status: res.status });
  } catch {
    return secureJson({ keys: [] }, { status: 200 });
  }
}

export async function POST(request: NextRequest) {
  if (!BACKEND_BASE || !ADMIN_KEY) {
    return secureJson(
      { error: "key_management_unavailable", message: "Key management is not configured." },
      { status: 503 },
    );
  }

  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return secureJson({ error: "invalid_json" }, { status: 400 });
  }

  const name = typeof body.name === "string" ? body.name.slice(0, 64) : "Unnamed Key";

  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
    const res = await fetch(`${BACKEND_BASE}/v1/keys`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Key": ADMIN_KEY,
      },
      body: JSON.stringify({ name, plan: "trial" }),
      signal: ctrl.signal,
    });
    clearTimeout(timer);
    const data = await res.json();
    return secureJson(data, { status: res.status });
  } catch {
    return secureJson(
      { error: "request_failed", message: "Could not reach backend." },
      { status: 502 },
    );
  }
}
