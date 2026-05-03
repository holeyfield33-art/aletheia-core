import { type NextRequest, NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";
import { APP_ORIGIN, MARKETING_ORIGIN } from "@/lib/site-config";

const BYPASS_PATHS = [
  "/api/stripe/checkout",
  "/api/stripe/webhook",
  "/api/webhooks/stripe",
  "/api/demo",
  "/_next/static",
];

const APP_HOST = new URL(APP_ORIGIN).host;
const MARKETING_HOST = new URL(MARKETING_ORIGIN).host;
const MARKETING_WWW_HOST = `www.${MARKETING_HOST}`;

function normalizedHost(request: NextRequest): string {
  const forwarded = request.headers.get("x-forwarded-host");
  const host = forwarded || request.headers.get("host") || "";
  return host.split(",")[0].trim().toLowerCase();
}

function stripPort(host: string): string {
  return host.replace(/:\d+$/, "");
}

function isAppRoute(pathname: string): boolean {
  return (
    pathname.startsWith("/dashboard") ||
    pathname.startsWith("/auth") ||
    pathname.startsWith("/login") ||
    pathname.startsWith("/signin") ||
    pathname.startsWith("/onboarding") ||
    pathname.startsWith("/api/auth")
  );
}

function isAlwaysLocalPath(pathname: string): boolean {
  return (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/api/") ||
    pathname === "/favicon.ico" ||
    pathname === "/robots.txt" ||
    pathname === "/sitemap.xml"
  );
}

function redirectToOrigin(
  request: NextRequest,
  origin: string,
  pathname: string,
): NextResponse {
  const target = new URL(pathname, origin);
  target.search = request.nextUrl.search;
  return NextResponse.redirect(target);
}

export default async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const host = stripPort(normalizedHost(request));

  if (host === APP_HOST) {
    if (pathname === "/") {
      return redirectToOrigin(request, APP_ORIGIN, "/dashboard");
    }
    if (!isAlwaysLocalPath(pathname) && !isAppRoute(pathname)) {
      return redirectToOrigin(request, MARKETING_ORIGIN, pathname);
    }
  }

  if (host === MARKETING_WWW_HOST) {
    if (isAppRoute(pathname)) {
      return redirectToOrigin(request, APP_ORIGIN, pathname);
    }
    return redirectToOrigin(request, MARKETING_ORIGIN, pathname);
  }

  if (host === MARKETING_HOST && isAppRoute(pathname)) {
    return redirectToOrigin(request, APP_ORIGIN, pathname);
  }

  const isBypassed = BYPASS_PATHS.some((path) => pathname.startsWith(path));

  // Route-level auth guard for authenticated zones.
  const protectedPaths = [
    "/onboarding",
    "/dashboard",
    "/api/keys",
    "/api/logs",
    "/api/evidence",
    "/api/account",
    "/api/settings",
    "/api/policy",
  ];
  const isProtected = protectedPaths.some((path) => pathname.startsWith(path));
  if (isProtected) {
    const token = await getToken({
      req: request,
      secret: process.env.NEXTAUTH_SECRET,
    });
    if (!token || token.deletedAt) {
      if (pathname.startsWith("/api/")) {
        return NextResponse.json({ error: "not_found" }, { status: 404 });
      }
      const loginUrl = new URL("/auth/login", request.url);
      loginUrl.searchParams.set("callbackUrl", pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  // CSRF protection for state-changing API routes.
  if (
    (request.method === "POST" ||
      request.method === "DELETE" ||
      request.method === "PUT" ||
      request.method === "PATCH") &&
    pathname.startsWith("/api/") &&
    !isBypassed &&
    !request.headers.has("x-api-key") &&
    !pathname.startsWith("/api/auth/") &&
    !pathname.startsWith("/api/webhooks/")
  ) {
    const origin = request.headers.get("origin");
    const referer = request.headers.get("referer");
    const host = request.headers.get("host");

    const sourceHost = origin
      ? (() => {
          try {
            return new URL(origin).host;
          } catch {
            return null;
          }
        })()
      : referer
        ? (() => {
            try {
              return new URL(referer).host;
            } catch {
              return null;
            }
          })()
        : null;

    if (!sourceHost || !host || sourceHost !== host) {
      return NextResponse.json(
        { error: "forbidden", reason: "csrf_origin_mismatch" },
        { status: 403 },
      );
    }
  }

  const nonce = crypto.randomUUID().replace(/-/g, "");
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-csp-nonce", nonce);

  const response = NextResponse.next({
    request: {
      headers: requestHeaders,
    },
  });
  response.headers.set("X-Content-Type-Options", "nosniff");
  response.headers.set("X-Frame-Options", "DENY");
  response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  response.headers.set("Cross-Origin-Opener-Policy", "same-origin");
  response.headers.set("Cross-Origin-Resource-Policy", "same-origin");
  response.headers.set(
    "Permissions-Policy",
    "camera=(), microphone=(), geolocation=()",
  );
  response.headers.set(
    "Strict-Transport-Security",
    "max-age=31536000; includeSubDomains; preload",
  );
  // CSP allowlist:
  // - connect-src is enumerated (no wildcard subdomain) so a future internal
  //   sub-host (admin, status, staging) does not become XHR-reachable from any
  //   XSS on the main app.
  // - Override the enumerated connect-src list at deploy time via
  //   CSP_EXTRA_CONNECT_SRC (space-separated origins) when adding new
  //   third-party endpoints.
  const extraConnect = (process.env.CSP_EXTRA_CONNECT_SRC ?? "").trim();
  const connectSrc = [
    "'self'",
    "https://api.stripe.com",
    "https://app.aletheia-core.com",
    "https://api.aletheia-core.com",
    "https://aletheia-core.onrender.com",
    "https://vitals.vercel-insights.com",
    extraConnect,
  ]
    .filter(Boolean)
    .join(" ");
  response.headers.set(
    "Content-Security-Policy",
    `default-src 'self'; script-src 'self' 'nonce-${nonce}' 'strict-dynamic' https://va.vercel-scripts.com; script-src-elem 'self' 'nonce-${nonce}' https://va.vercel-scripts.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src ${connectSrc}; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'`,
  );

  return response;
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
