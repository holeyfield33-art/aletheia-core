import { NextRequest, NextResponse } from "next/server";

/**
 * Demo proxy route — keeps ALETHEIA_DEMO_API_KEY server-side only.
 * Only proxies POST to the specific /v1/audit endpoint.
 * No arbitrary path proxying.
 */

const BACKEND_BASE = process.env.ALETHEIA_BACKEND_URL ?? "";
const DEMO_API_KEY = process.env.ALETHEIA_DEMO_API_KEY ?? "";
const TIMEOUT_MS = 12_000;

const SANITIZED_ERROR = { error: "request_failed" };

function validateBackendUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    // Must be HTTPS in production
    if (parsed.protocol !== "https:") return false;
    // Must be a known Aletheia host — not localhost or internal IPs
    const allowedHosts = (
      process.env.ALETHEIA_ALLOWED_BACKEND_HOSTS ??
      "onrender.com,aletheia-core.com"
    ).split(",").map((h) => h.trim());
    return allowedHosts.some((h) => parsed.hostname.endsWith(h));
  } catch {
    return false;
  }
}

// Allowed action values for demo (prevents abuse of the proxy)
const ALLOWED_ACTIONS = new Set([
  "fetch_data",
  "read_config",
  "Transfer_Funds",
  "Modify_Auth_Registry",
  "Bulk_Delete_Resource",
  "Open_External_Socket",
  "Approve_Loan_Disbursement",
  "Initiate_ACH",
  "exec_code",
  "DEMO_ACTION",
]);

const MAX_DEMO_BODY_BYTES = 50_000; // 50 KB — generous for demo payloads

export async function POST(request: NextRequest) {
  const contentLength = Number(request.headers.get("content-length") ?? "0");
  if (contentLength > MAX_DEMO_BODY_BYTES) {
    return NextResponse.json({ error: "payload_too_large" }, { status: 413 });
  }

  if (!BACKEND_BASE) {
    console.error("[demo-proxy] ALETHEIA_BACKEND_URL not configured");
    return NextResponse.json(SANITIZED_ERROR, { status: 503 });
  }

  if (!validateBackendUrl(BACKEND_BASE)) {
    console.error("[demo-proxy] ALETHEIA_BACKEND_URL failed validation:", BACKEND_BASE);
    return NextResponse.json(SANITIZED_ERROR, { status: 503 });
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "invalid_request" }, { status: 400 });
  }

  if (
    typeof body !== "object" ||
    body === null ||
    typeof (body as Record<string, unknown>).payload !== "string"
  ) {
    return NextResponse.json({ error: "invalid_request" }, { status: 400 });
  }

  const { payload, origin, action } = body as Record<string, unknown>;

  // Sanitize and bound inputs
  const safePayload = String(payload).slice(0, 2000);
  const safeOrigin =
    typeof origin === "string" ? origin.slice(0, 64) : "demo-client";
  const safeAction =
    typeof action === "string" && ALLOWED_ACTIONS.has(action)
      ? action
      : "DEMO_ACTION";

  const auditBody = {
    payload: safePayload,
    origin: safeOrigin,
    action: safeAction,
  };

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const upstream = await fetch(`${BACKEND_BASE}/v1/audit`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(DEMO_API_KEY ? { "X-API-Key": DEMO_API_KEY } : {}),
      },
      body: JSON.stringify(auditBody),
      signal: controller.signal,
    });

    clearTimeout(timer);

    if (!upstream.ok) {
      // Do not forward raw upstream error bodies — return sanitized message
      console.error(`[demo-proxy] upstream returned ${upstream.status}`);
      return NextResponse.json(SANITIZED_ERROR, { status: 503 });
    }

    const data = await upstream.json();
    return NextResponse.json(data);
  } catch (err) {
    clearTimeout(timer);
    const isTimeout =
      err instanceof Error &&
      (err.name === "AbortError" || err.message.includes("abort"));
    if (!isTimeout) {
      // Log non-timeout errors without exposing details
      console.error("[demo-proxy] upstream fetch failed:", err instanceof Error ? err.message : "unknown");
    }
    return NextResponse.json(SANITIZED_ERROR, { status: 503 });
  }
}

// Reject all other methods
export async function GET() {
  return NextResponse.json({ error: "method_not_allowed" }, { status: 405 });
}

export async function PUT() {
  return NextResponse.json({ error: "method_not_allowed" }, { status: 405 });
}

export async function DELETE() {
  return NextResponse.json({ error: "method_not_allowed" }, { status: 405 });
}
