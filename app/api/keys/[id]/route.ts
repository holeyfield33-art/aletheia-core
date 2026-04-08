import { NextRequest, NextResponse } from "next/server";

/**
 * Per-key management proxy.
 *
 * GET    /api/keys/[id]  → get key usage
 * DELETE /api/keys/[id]  → revoke key
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

function extractId(request: NextRequest): string | null {
  const parts = request.nextUrl.pathname.split("/");
  // /api/keys/[id] → last segment
  const id = parts[parts.length - 1];
  if (!id || id.length > 64 || !/^[a-f0-9]+$/.test(id)) return null;
  return id;
}

export async function GET(request: NextRequest) {
  const id = extractId(request);
  if (!id) return secureJson({ error: "invalid_key_id" }, { status: 400 });
  if (!BACKEND_BASE || !ADMIN_KEY) {
    return secureJson({ error: "not_configured" }, { status: 503 });
  }

  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
    const res = await fetch(`${BACKEND_BASE}/v1/keys/${id}/usage`, {
      method: "GET",
      headers: { "X-Admin-Key": ADMIN_KEY },
      signal: ctrl.signal,
    });
    clearTimeout(timer);
    const data = await res.json();
    return secureJson(data, { status: res.status });
  } catch {
    return secureJson({ error: "request_failed" }, { status: 502 });
  }
}

export async function DELETE(request: NextRequest) {
  const id = extractId(request);
  if (!id) return secureJson({ error: "invalid_key_id" }, { status: 400 });
  if (!BACKEND_BASE || !ADMIN_KEY) {
    return secureJson({ error: "not_configured" }, { status: 503 });
  }

  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
    const res = await fetch(`${BACKEND_BASE}/v1/keys/${id}`, {
      method: "DELETE",
      headers: { "X-Admin-Key": ADMIN_KEY },
      signal: ctrl.signal,
    });
    clearTimeout(timer);
    const data = await res.json();
    return secureJson(data, { status: res.status });
  } catch {
    return secureJson({ error: "request_failed" }, { status: 502 });
  }
}
