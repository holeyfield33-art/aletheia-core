import { NextRequest, NextResponse } from "next/server";

const BACKEND_BASE = (
  process.env.ALETHEIA_BACKEND_URL ??
  process.env.ALETHEIA_BASE_URL ??
  "https://aletheia-core.onrender.com"
).trim();

const ALLOWED_METHODS = new Set(["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]);

function secureGatewayError(status: number): NextResponse {
  return NextResponse.json(
    { error: "gateway_unavailable" },
    {
      status,
      headers: {
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
      },
    },
  );
}

function buildBackendUrl(pathSegments: string[], search: string): URL {
  const backend = new URL(BACKEND_BASE);
  const cleanPath = pathSegments.map((segment) => encodeURIComponent(segment)).join("/");
  backend.pathname = `/v1/${cleanPath}`;
  backend.search = search;
  return backend;
}

async function proxyToBackend(
  request: NextRequest,
  context: { params: Promise<{ path?: string[] }> },
): Promise<NextResponse> {
  if (!ALLOWED_METHODS.has(request.method)) {
    return NextResponse.json({ error: "method_not_allowed" }, { status: 405 });
  }

  let pathSegments: string[] = [];
  try {
    const params = await context.params;
    pathSegments = params.path ?? [];
  } catch {
    return secureGatewayError(400);
  }

  if (pathSegments.length === 0) {
    return NextResponse.json({ error: "not_found" }, { status: 404 });
  }

  const targetUrl = buildBackendUrl(pathSegments, request.nextUrl.search);

  const headers = new Headers(request.headers);
  headers.set("x-forwarded-host", request.headers.get("host") ?? "");

  const body = request.method === "GET" || request.method === "OPTIONS"
    ? undefined
    : await request.arrayBuffer();

  try {
    const upstream = await fetch(targetUrl.toString(), {
      method: request.method,
      headers,
      body,
    });

    const upstreamBody = await upstream.arrayBuffer();
    const responseHeaders = new Headers(upstream.headers);
    responseHeaders.set("Cache-Control", "no-store");
    responseHeaders.set("X-Content-Type-Options", "nosniff");

    return new NextResponse(upstreamBody, {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch {
    return secureGatewayError(503);
  }
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path?: string[] }> },
): Promise<NextResponse> {
  return proxyToBackend(request, context);
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ path?: string[] }> },
): Promise<NextResponse> {
  return proxyToBackend(request, context);
}

export async function PUT(
  request: NextRequest,
  context: { params: Promise<{ path?: string[] }> },
): Promise<NextResponse> {
  return proxyToBackend(request, context);
}

export async function PATCH(
  request: NextRequest,
  context: { params: Promise<{ path?: string[] }> },
): Promise<NextResponse> {
  return proxyToBackend(request, context);
}

export async function DELETE(
  request: NextRequest,
  context: { params: Promise<{ path?: string[] }> },
): Promise<NextResponse> {
  return proxyToBackend(request, context);
}

export async function OPTIONS(
  request: NextRequest,
  context: { params: Promise<{ path?: string[] }> },
): Promise<NextResponse> {
  return proxyToBackend(request, context);
}
