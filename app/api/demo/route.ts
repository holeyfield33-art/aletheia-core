import { NextRequest, NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";
import { secureJson as _baseSecureJson } from "@/lib/api-utils";
import { PRICING } from "@/lib/site-config";

/**
 * Demo proxy route — keeps ALETHEIA_DEMO_API_KEY server-side only.
 * Only proxies POST to the specific /v1/audit endpoint.
 * No arbitrary path proxying.
 */

const BACKEND_BASE = process.env.ALETHEIA_BACKEND_URL ?? "";
const DEMO_API_KEY = (
  process.env.ALETHEIA_DEMO_API_KEY ??
  process.env.ALETHEIA_API_KEY ??
  ""
).trim();
const TIMEOUT_MS = 25_000; // Render free-tier cold starts take 15-30s
const ACTIVE_MODE = process.env.ACTIVE_MODE;

/** Allow Vercel to keep the function alive long enough for cold starts. */
export const maxDuration = 30;

const SANITIZED_ERROR = { error: "request_failed" };
const FREE_TIER_EXHAUSTED_MESSAGE = `You've used your ${PRICING.free.receipts.toLocaleString()} free Sovereign Audit Receipts. Upgrade to continue receiving cryptographic proof of AI safety.`;

/** CORS headers specific to the demo proxy. */
const corsHeaders: Record<string, string> = {
  "X-XSS-Protection": "0",
  "Access-Control-Allow-Origin": process.env.ALETHEIA_CORS_ORIGIN ?? "https://app.aletheia-core.com",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
  "Access-Control-Max-Age": "600",
};

/** Wrap base secureJson with demo CORS headers. */
function secureJson(body: unknown, init?: { status?: number; headers?: Record<string, string> }) {
  return _baseSecureJson(body, { ...init, headers: { ...corsHeaders, ...(init?.headers ?? {}) } });
}

function validateBackendUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    // Must be HTTPS in production
    if (parsed.protocol !== "https:") return false;
    // Must be a known Aletheia host — exact match or subdomain only
    const allowedHosts = (
      process.env.ALETHEIA_ALLOWED_BACKEND_HOSTS ??
      "onrender.com,aletheia-core.com"
    ).split(",").map((h) => h.trim());
    return allowedHosts.some((h) =>
      parsed.hostname === h || parsed.hostname.endsWith(`.${h}`)
    );
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

const MAX_DEMO_BODY_BYTES = 25_000; // 25 KB — bounded for demo payloads
const MAX_BODY_CHARS = 25_000; // raw character limit before JSON parse

export async function POST(request: NextRequest) {
  // Production mode gate
  if (process.env.ENVIRONMENT === "production" && ACTIVE_MODE !== "true") {
    console.error("[demo-proxy] ACTIVE_MODE is not 'true' in production");
    return secureJson({ error: "service_unavailable" }, { status: 503 });
  }

  const contentLength = Number(request.headers.get("content-length") ?? "0");
  if (contentLength > MAX_DEMO_BODY_BYTES) {
    return secureJson({ error: "payload_too_large" }, { status: 413 });
  }

  if (!BACKEND_BASE) {
    console.error("[demo-proxy] ALETHEIA_BACKEND_URL not configured");
    return secureJson(SANITIZED_ERROR, { status: 503 });
  }

  if (!validateBackendUrl(BACKEND_BASE)) {
    console.error("[demo-proxy] ALETHEIA_BACKEND_URL failed validation:", BACKEND_BASE);
    return secureJson(SANITIZED_ERROR, { status: 503 });
  }

  if (!DEMO_API_KEY) {
    console.error("[demo-proxy] No demo API key configured (ALETHEIA_DEMO_API_KEY/ALETHEIA_API_KEY)");
    return secureJson({ error: "service_unavailable" }, { status: 503 });
  }

  // Raw body size check (character count)
  let rawText: string;
  try {
    rawText = await request.text();
  } catch {
    return secureJson({ error: "invalid_request" }, { status: 400 });
  }
  if (rawText.length > MAX_BODY_CHARS) {
    return secureJson({ error: "payload_too_large" }, { status: 413 });
  }

  let body: unknown;
  try {
    body = JSON.parse(rawText);
  } catch {
    return secureJson({ error: "invalid_request" }, { status: 400 });
  }

  if (
    typeof body !== "object" ||
    body === null ||
    typeof (body as Record<string, unknown>).payload !== "string"
  ) {
    return secureJson({ error: "invalid_request" }, { status: 400 });
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
      console.error(`[demo-proxy] upstream returned ${upstream.status}`);
      if (upstream.status === 429) {
        const token = await getToken({ req: request, secret: process.env.NEXTAUTH_SECRET });
        const upgradeUrl = token?.sub
          ? "/api/stripe/checkout?tier=scale"
          : `/auth/register?callbackUrl=${encodeURIComponent("/pricing?tier=scale")}`;
        return secureJson(
          {
            error: "free_tier_exhausted",
            message: FREE_TIER_EXHAUSTED_MESSAGE,
            upgradeUrl,
          },
          { status: 402, headers: { "X-Upgrade-Url": upgradeUrl } },
        );
      }
      if (upstream.status === 401) {
        return secureJson({ error: "unauthorized" }, { status: 401 });
      }
      // Forward 403 with the structured decision body so the demo UI
      // can display educational security-block messaging.
      if (upstream.status === 403) {
        try {
          const denied = await upstream.json();
          return secureJson(denied, { status: 403 });
        } catch {
          return secureJson(
            { decision: "DENIED", reason: "security_block" },
            { status: 403 },
          );
        }
      }
      return secureJson(SANITIZED_ERROR, { status: 503 });
    }

    const data = await upstream.json();
    return secureJson(data);
  } catch (err) {
    clearTimeout(timer);
    const isTimeout =
      err instanceof Error &&
      (err.name === "AbortError" || err.message.includes("abort"));
    if (!isTimeout) {
      // Log non-timeout errors without exposing details
      console.error("[demo-proxy] upstream fetch failed:", err instanceof Error ? err.message : "unknown");
    }
    return secureJson(SANITIZED_ERROR, { status: 503 });
  }
}

// OPTIONS preflight handler
export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers: corsHeaders });
}

// Reject all other methods
export async function GET() {
  return secureJson({ error: "method_not_allowed" }, { status: 405 });
}

export async function PUT() {
  return secureJson({ error: "method_not_allowed" }, { status: 405 });
}

export async function DELETE() {
  return secureJson({ error: "method_not_allowed" }, { status: 405 });
}
