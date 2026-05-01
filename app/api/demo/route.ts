import { NextRequest, NextResponse } from "next/server";
import { isIP } from "node:net";
import { getToken } from "next-auth/jwt";
import { secureJson as _baseSecureJson } from "@/lib/api-utils";
import { consumeRateLimit } from "@/lib/rate-limit";
import { PRICING } from "@/lib/site-config";
import { incrementUsage } from "@/lib/usage-tracking";

/**
 * Demo proxy route — keeps ALETHEIA_DEMO_API_KEY server-side only.
 * Only proxies POST to the specific /v1/audit endpoint.
 * No arbitrary path proxying.
 */

const BACKEND_BASE = (
  process.env.ALETHEIA_BACKEND_URL ??
  process.env.ALETHEIA_BASE_URL ??
  "https://api.aletheia-core.com"
).trim();
const BACKEND_FALLBACK_BASE = "https://aletheia-core.onrender.com";
const DEMO_API_KEY = (
  process.env.ALETHEIA_DEMO_API_KEY ??
  process.env.ALETHEIA_API_KEY ??
  ""
).trim();
const TIMEOUT_MS = parseInt(
  process.env.DEMO_UPSTREAM_TIMEOUT_MS ?? "45000",
  10,
);
const ACTIVE_MODE = (process.env.ACTIVE_MODE ?? "").trim().toLowerCase();

/** Allow Vercel to keep the function alive long enough for cold starts. */
export const maxDuration = 60;

const SANITIZED_ERROR = { error: "request_failed" };
const FREE_TIER_EXHAUSTED_MESSAGE = `You've used your ${PRICING.free.receipts.toLocaleString()} free Sovereign Audit Receipts. Upgrade to continue receiving cryptographic proof of AI safety.`;

/** CORS headers specific to the demo proxy. */
const corsHeaders: Record<string, string> = {
  "X-XSS-Protection": "0",
  "Access-Control-Allow-Origin":
    process.env.ALETHEIA_CORS_ORIGIN ?? "https://app.aletheia-core.com",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
  "Access-Control-Max-Age": "600",
};

/** Wrap base secureJson with demo CORS headers. */
function secureJson(
  body: unknown,
  init?: { status?: number; headers?: Record<string, string> },
) {
  return _baseSecureJson(body, {
    ...init,
    headers: { ...corsHeaders, ...(init?.headers ?? {}) },
  });
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
    )
      .split(",")
      .map((h) => h.trim());
    return allowedHosts.some(
      (h) => parsed.hostname === h || parsed.hostname.endsWith(`.${h}`),
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

// Per-IP rate limit on the public demo proxy. Without this, an attacker can
// burn the shared demo API key's monthly quota in seconds and break the
// top-of-funnel for every visitor. Tunable via env.
const TRUST_CF_HEADERS = process.env.TRUST_CF_HEADERS === "true";
const DEMO_RATE_LIMIT = parseInt(process.env.DEMO_RATE_LIMIT ?? "20", 10);
const DEMO_RATE_WINDOW_MS = parseInt(
  process.env.DEMO_RATE_WINDOW_MS ?? String(60 * 60 * 1000),
  10,
);

function extractClientIp(request: NextRequest): string {
  if (TRUST_CF_HEADERS) {
    const cf = request.headers.get("cf-connecting-ip")?.trim();
    if (cf && isIP(cf)) return cf;
  }
  const forwardedFor = request.headers.get("x-forwarded-for");
  if (forwardedFor) {
    const candidate = forwardedFor
      .split(",")
      .map((v) => v.trim())
      .reverse()
      .find((v) => isIP(v));
    if (candidate) return candidate;
  }
  return "unknown";
}

export async function POST(request: NextRequest) {
  // Do not block demo in production if ACTIVE_MODE is simply unset in frontend envs.
  if (
    process.env.ENVIRONMENT === "production" &&
    ACTIVE_MODE &&
    ACTIVE_MODE !== "true"
  ) {
    console.error("[demo-proxy] ACTIVE_MODE is not 'true' in production");
    return secureJson({ error: "service_unavailable" }, { status: 503 });
  }

  const contentLength = Number(request.headers.get("content-length") ?? "0");
  if (contentLength > MAX_DEMO_BODY_BYTES) {
    return secureJson({ error: "payload_too_large" }, { status: 413 });
  }

  // Per-IP rate limit before any upstream work. Fail CLOSED on DB error so a
  // Postgres outage cannot turn the demo into an open relay that drains the
  // shared upstream key's quota.
  const clientIp = extractClientIp(request);
  if (clientIp !== "unknown") {
    let rl: {
      allowed: boolean;
      retryAfterSeconds: number;
      remaining: number;
    } | null = null;
    try {
      rl = await consumeRateLimit({
        action: "demo_proxy",
        key: clientIp,
        limit: DEMO_RATE_LIMIT,
        windowMs: DEMO_RATE_WINDOW_MS,
      });
    } catch (err) {
      console.error(
        "[demo-proxy] rate limit DB error — failing closed:",
        err instanceof Error ? err.message : "unknown",
      );
      return secureJson(
        {
          error: "service_unavailable",
          message: "Demo is temporarily unavailable. Please try again shortly.",
        },
        { status: 503, headers: { "Retry-After": "30" } },
      );
    }
    if (rl && !rl.allowed) {
      return secureJson(
        {
          error: "rate_limited",
          message:
            "Demo rate limit reached. Sign up for a free API key for higher limits.",
        },
        {
          status: 429,
          headers: {
            "Retry-After": String(rl.retryAfterSeconds),
            "X-RateLimit-Limit": String(DEMO_RATE_LIMIT),
            "X-RateLimit-Remaining": "0",
          },
        },
      );
    }
    // Stash remaining for response headers later (success path).
    (request as unknown as { _rlRemaining?: number })._rlRemaining =
      rl?.remaining;
  }

  const backendCandidates = [BACKEND_BASE, BACKEND_FALLBACK_BASE].filter(
    (value, index, arr) => value && arr.indexOf(value) === index,
  );

  if (backendCandidates.length === 0) {
    console.error("[demo-proxy] No backend URL configured");
    return secureJson(SANITIZED_ERROR, { status: 503 });
  }

  if (!backendCandidates.every(validateBackendUrl)) {
    console.error(
      "[demo-proxy] Backend URL failed validation:",
      backendCandidates,
    );
    return secureJson(SANITIZED_ERROR, { status: 503 });
  }

  if (!DEMO_API_KEY) {
    console.error(
      "[demo-proxy] No demo API key configured (ALETHEIA_DEMO_API_KEY/ALETHEIA_API_KEY)",
    );
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

  let upstream: Response | null = null;
  try {
    // Retry once against fallback host when primary backend is unreachable or 5xx.
    for (let i = 0; i < backendCandidates.length; i += 1) {
      const base = backendCandidates[i];
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
      try {
        const res = await fetch(`${base}/v1/audit`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(DEMO_API_KEY ? { "X-API-Key": DEMO_API_KEY } : {}),
          },
          body: JSON.stringify(auditBody),
          signal: controller.signal,
        });
        upstream = res;
        if (res.status < 500 || i === backendCandidates.length - 1) {
          break;
        }
        console.error(
          `[demo-proxy] upstream ${base} returned ${res.status}; trying fallback`,
        );
      } catch (err) {
        if (i === backendCandidates.length - 1) {
          throw err;
        }
        console.error(
          `[demo-proxy] upstream fetch failed for ${base}; trying fallback:`,
          err instanceof Error ? err.message : "unknown",
        );
      } finally {
        clearTimeout(timer);
      }
    }

    if (!upstream) {
      return secureJson(SANITIZED_ERROR, { status: 503 });
    }

    if (!upstream.ok) {
      console.error(`[demo-proxy] upstream returned ${upstream.status}`);
      if (upstream.status === 429) {
        const token = await getToken({
          req: request,
          secret: process.env.NEXTAUTH_SECRET,
        });
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
        // Upstream rejected our shared demo key. Most common cause: the key
        // configured in ALETHEIA_DEMO_API_KEY is not present in the Render
        // KeyStore (e.g. wiped by a restart on an ephemeral SQLite backend).
        // See docs/LAUNCH_GUIDE.md → "Hosted demo key persistence".
        console.error(
          "[demo-proxy] upstream returned 401 — demo key not registered in backend KeyStore",
        );
        return secureJson(
          {
            error: "demo_unavailable",
            message:
              "Demo backend is temporarily unavailable. Please try again later.",
          },
          { status: 503 },
        );
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

    // Metered PAYG usage is tracked asynchronously so request latency is unaffected.
    const token = await getToken({
      req: request,
      secret: process.env.NEXTAUTH_SECRET,
    });
    if (token?.sub && token.plan === "ENTERPRISE") {
      void incrementUsage(token.sub, 1).catch((error) => {
        console.error("[demo-proxy] Usage tracking failed", {
          userId: token.sub,
          error,
        });
      });
    }

    const remaining = (request as unknown as { _rlRemaining?: number })
      ._rlRemaining;
    const rateHeaders: Record<string, string> | undefined =
      typeof remaining === "number"
        ? {
            "X-RateLimit-Limit": String(DEMO_RATE_LIMIT),
            "X-RateLimit-Remaining": String(Math.max(0, remaining)),
          }
        : undefined;
    return secureJson(data, { headers: rateHeaders });
  } catch (err) {
    const isTimeout =
      err instanceof Error &&
      (err.name === "AbortError" || err.message.includes("abort"));
    if (!isTimeout) {
      // Log non-timeout errors without exposing details
      console.error(
        "[demo-proxy] upstream fetch failed:",
        err instanceof Error ? err.message : "unknown",
      );
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
