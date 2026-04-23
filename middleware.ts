import { type NextRequest, NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Route-level auth guard for authenticated zones
  const protectedPaths = ["/dashboard", "/api/keys", "/api/logs", "/api/evidence", "/api/account", "/api/settings"];
  const isProtected = protectedPaths.some((p) => pathname.startsWith(p));
  if (isProtected) {
    const token = await getToken({
      req: request,
      secret: process.env.NEXTAUTH_SECRET,
    });
    if (!token) {
      // For API routes return 401; for page routes redirect to login
      if (pathname.startsWith("/api/")) {
        return NextResponse.json({ error: "unauthorized" }, { status: 401 });
      }
      const loginUrl = new URL("/auth/login", request.url);
      loginUrl.searchParams.set("callbackUrl", encodeURIComponent(pathname));
      return NextResponse.redirect(loginUrl);
    }
  }

  // CSRF protection for state-changing API routes
  if (
    (request.method === "POST" || request.method === "DELETE" || request.method === "PUT" || request.method === "PATCH") &&
    pathname.startsWith("/api/") &&
    !pathname.startsWith("/api/auth/") &&
    !pathname.startsWith("/api/webhooks/")
  ) {
    const origin = request.headers.get("origin");
    const referer = request.headers.get("referer");
    const host = request.headers.get("host");

    // Require at least one of Origin or Referer
    const sourceHost = origin
      ? (() => { try { return new URL(origin).host; } catch { return null; } })()
      : referer
        ? (() => { try { return new URL(referer).host; } catch { return null; } })()
        : null;

    if (!sourceHost || !host || sourceHost !== host) {
      return NextResponse.json({ error: "forbidden" }, { status: 403 });
    }
  }

  // Apply security headers to all responses
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
    "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self' https://api.stripe.com https://*.aletheia-core.com; frame-ancestors 'none'",
  );

  return response;
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
