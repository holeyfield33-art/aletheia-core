import { type NextRequest, NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";

const BYPASS_PATHS = [
  "/api/stripe/checkout",
  "/api/stripe/webhook",
  "/api/webhooks/stripe",
  "/_next/static",
];

export default async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isBypassed = BYPASS_PATHS.some((path) => pathname.startsWith(path));

  // Route-level auth guard for authenticated zones.
  const protectedPaths = [
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
        return NextResponse.json({ error: "unauthorized" }, { status: 401 });
      }
      const loginUrl = new URL("/auth/login", request.url);
      loginUrl.searchParams.set("callbackUrl", pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  // CSRF protection for state-changing API routes.
  if (
    (request.method === "POST" || request.method === "DELETE" || request.method === "PUT" || request.method === "PATCH") &&
    pathname.startsWith("/api/") &&
    !isBypassed &&
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
      return NextResponse.json({ error: "forbidden" }, { status: 403 });
    }
  }

  const response = NextResponse.next();
  response.headers.set("X-Content-Type-Options", "nosniff");
  response.headers.set("X-Frame-Options", "DENY");
  response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  response.headers.set(
    "Strict-Transport-Security",
    "max-age=31536000; includeSubDomains",
  );
  response.headers.set(
    "Content-Security-Policy",
    "default-src 'self'; script-src 'self' 'unsafe-inline' https://va.vercel-scripts.com; script-src-elem 'self' 'unsafe-inline' https://va.vercel-scripts.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self' https://api.stripe.com https://*.aletheia-core.com https://vitals.vercel-insights.com; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'",
  );

  return response;
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
