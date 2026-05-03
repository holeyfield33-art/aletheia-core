import { NextRequest, NextResponse } from "next/server";
import { isIP } from "node:net";
import { createHmac, randomUUID } from "node:crypto";
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
  "https://aletheia-core.onrender.com"
).trim();
const BACKEND_URLS = (process.env.ALETHEIA_BACKEND_URLS ?? "")
  .split(",")
  .map((u) => u.trim())
  .filter(Boolean);
const BACKEND_FALLBACK_BASE = "https://aletheia-core.onrender.com";
// BACKEND_SECONDARY_BASE intentionally removed — api.aletheia-core.com has no dedicated backend host
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
const TRANSIENT_UPSTREAM_STATUS = new Set([502, 503, 504]);
const MAX_UPSTREAM_ATTEMPTS_PER_BACKEND = Math.max(
  1,
  parseInt(process.env.DEMO_UPSTREAM_ATTEMPTS_PER_BACKEND ?? "2", 10),
);
const RETRY_BACKOFF_MS = Math.max(
  50,
  parseInt(process.env.DEMO_UPSTREAM_RETRY_BACKOFF_MS ?? "250", 10),
);
const NON_BLOCKING_FAILOVER_STATUSES = new Set([400, 401, 404, 405, 408, 421]);

/** Allow Vercel to keep the function alive long enough for cold starts. */
export const maxDuration = 60;

const SANITIZED_ERROR = { error: "request_failed" };
const FREE_TIER_EXHAUSTED_MESSAGE = `You've used your ${PRICING.free.receipts.toLocaleString()} free Sovereign Audit Receipts. Upgrade to continue receiving cryptographic proof of AI safety.`;

/** CORS headers specific to the demo proxy. */
const corsHeaders: Record<string, string> = {
  "X-XSS-Protection": "0",
  "Access-Control-Allow-Origin":
    process.env.ALETHEIA_CORS_ORIGIN ?? "https://aletheia-core.com",
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

function isTransientUpstreamStatus(status: number): boolean {
  return TRANSIENT_UPSTREAM_STATUS.has(status);
}

function shouldFailoverToNextBackend(status: number): boolean {
  return NON_BLOCKING_FAILOVER_STATUSES.has(status) || isTransientUpstreamStatus(status);
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
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

// ---------------------------------------------------------------------------
// Server-side injection guard — runs before the upstream call.
// Matches canonical prompt-injection / exfiltration attack patterns and
// returns a hard DENIED receipt so the demo is never degraded-engine-bypassed.
// ---------------------------------------------------------------------------
const INJECTION_PATTERNS: { re: RegExp; rule_id: string; severity: string }[] =
  [
    {
      re: /ignore\s+(all|any|previous|prior)\s+instructions/i,
      rule_id: "INJECTION_IGNORE_INSTRUCTIONS",
      severity: "CRITICAL",
    },
    {
      re: /forget\s+(your\s+)?(rules|instructions|prompt|training)/i,
      rule_id: "INJECTION_FORGET_RULES",
      severity: "CRITICAL",
    },
    {
      re: /you\s+are\s+(now\s+)?(DAN|admin|root|developer\s+mode|jailbreak)/i,
      rule_id: "INJECTION_ROLE_OVERRIDE",
      severity: "CRITICAL",
    },
    {
      re: /system\s+prompt/i,
      rule_id: "INJECTION_SYSTEM_PROMPT",
      severity: "HIGH",
    },
    {
      re: /read\s+\.env/i,
      rule_id: "EXFIL_ENV_FILE",
      severity: "CRITICAL",
    },
    {
      re: /exfiltrate/i,
      rule_id: "EXFIL_DATA",
      severity: "CRITICAL",
    },
    {
      re: /POST\s+(keys|secrets?|tokens?|credentials?)\s+to\s+/i,
      rule_id: "EXFIL_CREDENTIAL_POST",
      severity: "CRITICAL",
    },
  ];

const GUARD_SIGN_SECRET = (
  process.env.DEMO_NONCE_SECRET ??
  process.env.NEXTAUTH_SECRET ??
  "demo-guard-fallback"
).slice(0, 128);

function buildDeniedReceipt(
  rule_id: string,
  severity: string,
  safeAction: string,
): Record<string, unknown> {
  const request_id = randomUUID();
  const policy_version = new Date().toISOString().slice(0, 10).replace(/-/g, ".");
  const receiptCore = {
    request_id,
    decision: "DENIED",
    rule_id,
    severity,
    action: safeAction,
    policy_version,
    semantic_engine: { degraded: false, manifest_version: policy_version, categories_checked: ["injection", "exfiltration"] },
  };
  const signature = createHmac("sha256", GUARD_SIGN_SECRET)
    .update(JSON.stringify(receiptCore))
    .digest("hex");
  return { ...receiptCore, signature };
}

function buildUpstreamUnavailableReceipt(
  safeAction: string,
): Record<string, unknown> {
  const request_id = randomUUID();
  const policy_version = new Date().toISOString().slice(0, 10).replace(/-/g, ".");
  const receiptCore = {
    request_id,
    decision: "DENIED",
    rule_id: "DEMO_UPSTREAM_UNAVAILABLE",
    severity: "HIGH",
    reason: "upstream_unavailable",
    action: safeAction,
    policy_version,
    semantic_engine: {
      degraded: true,
      manifest_version: policy_version,
      categories_checked: ["availability_guard"],
    },
  };
  const signature = createHmac("sha256", GUARD_SIGN_SECRET)
    .update(JSON.stringify(receiptCore))
    .digest("hex");
  return { ...receiptCore, signature };
}

function extractInjectionMatch(
  payload: string,
): { rule_id: string; severity: string } | null {
  for (const { re, rule_id, severity } of INJECTION_PATTERNS) {
    if (re.test(payload)) return { rule_id, severity };
  }
  return null;
}

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

  const backendCandidates = (BACKEND_URLS.length
    ? BACKEND_URLS
    : [BACKEND_BASE, BACKEND_FALLBACK_BASE]
  ).filter((value, index, arr) => value && arr.indexOf(value) === index);

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

  // Hard injection guard — must run before upstream call regardless of engine state.
  const injectionMatch = extractInjectionMatch(safePayload);
  if (injectionMatch) {
    return secureJson(
      buildDeniedReceipt(injectionMatch.rule_id, injectionMatch.severity, safeAction),
    );
  }

  const auditBody = {
    payload: safePayload,
    origin: safeOrigin,
    action: safeAction,
  };

  let upstream: Response | null = null;
  try {
    // Retry transient 5xx/network errors per backend, then fail over to the next backend.
    let lastFetchError: unknown = null;
    for (let i = 0; i < backendCandidates.length; i += 1) {
      const base = backendCandidates[i];
      const hasMoreBackends = i < backendCandidates.length - 1;
      let shouldTryNextBackend = false;

      for (
        let attempt = 1;
        attempt <= MAX_UPSTREAM_ATTEMPTS_PER_BACKEND;
        attempt += 1
      ) {
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
          const shouldRetrySameBackend =
            isTransientUpstreamStatus(res.status) &&
            attempt < MAX_UPSTREAM_ATTEMPTS_PER_BACKEND;

          if (shouldRetrySameBackend) {
            const backoff = RETRY_BACKOFF_MS * 2 ** (attempt - 1);
            console.error(
              "[demo-proxy] upstream %s returned %d; retrying in %dms (attempt %d/%d)",
              base,
              res.status,
              backoff,
              attempt,
              MAX_UPSTREAM_ATTEMPTS_PER_BACKEND,
            );
            await sleep(backoff);
            continue;
          }

          if (
            !res.ok &&
            hasMoreBackends &&
            shouldFailoverToNextBackend(res.status) &&
            res.status !== 403 &&
            res.status !== 429
          ) {
            shouldTryNextBackend = true;
            upstream = null;
            console.error(
              "[demo-proxy] upstream %s returned %d; failing over to %s",
              base,
              res.status,
              backendCandidates[i + 1],
            );
          }

          // Stop retrying this backend once we have either success or a non-transient status.
          break;
        } catch (err) {
          lastFetchError = err;
          const canRetrySameBackend =
            attempt < MAX_UPSTREAM_ATTEMPTS_PER_BACKEND;
          if (canRetrySameBackend) {
            const backoff = RETRY_BACKOFF_MS * 2 ** (attempt - 1);
            console.error(
              "[demo-proxy] upstream fetch failed for %s; retrying in %dms (attempt %d/%d): %s",
              base,
              backoff,
              attempt,
              MAX_UPSTREAM_ATTEMPTS_PER_BACKEND,
              err instanceof Error ? err.message : "unknown",
            );
            await sleep(backoff);
            continue;
          }
          console.error(
            "[demo-proxy] upstream fetch failed for %s; trying next backend: %s",
            base,
            err instanceof Error ? err.message : "unknown",
          );
        } finally {
          clearTimeout(timer);
        }
      }

      if (shouldTryNextBackend) {
        continue;
      }

      if (upstream && (!upstream.status || !isTransientUpstreamStatus(upstream.status))) {
        break;
      }

      if (hasMoreBackends) {
        console.error(
          "[demo-proxy] failing over from %s to %s",
          base,
          backendCandidates[i + 1],
        );
      } else if (lastFetchError) {
        throw lastFetchError;
      }
    }

    if (!upstream) {
      return secureJson(buildUpstreamUnavailableReceipt(safeAction), {
        status: 503,
        headers: { "Retry-After": "10" },
      });
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
      if (isTransientUpstreamStatus(upstream.status)) {
        return secureJson(
          {
            error: "service_unavailable",
            message:
              "Demo backend is warming up. Please retry in a few seconds.",
          },
          { status: 503, headers: { "Retry-After": "10" } },
        );
      }
      return secureJson(buildUpstreamUnavailableReceipt(safeAction), {
        status: 503,
        headers: { "Retry-After": "10" },
      });
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
    return secureJson(buildUpstreamUnavailableReceipt(safeAction), {
      status: 503,
      headers: { "Retry-After": isTimeout ? "5" : "10" },
    });
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
