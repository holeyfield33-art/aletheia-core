import { NextResponse } from "next/server";

export const SECURITY_HEADERS = {
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
  "X-XSS-Protection": "1; mode=block",
  "Referrer-Policy": "strict-origin-when-cross-origin",
} as const;

export function secureJson<T>(
  data: T,
  init?: ResponseInit & { headers?: Record<string, string> },
): NextResponse<T> {
  return NextResponse.json(data, {
    ...init,
    headers: {
      ...SECURITY_HEADERS,
      ...(init?.headers ?? {}),
    },
  });
}

export function apiError(
  status: number,
  error: string,
  message?: string,
): NextResponse {
  return secureJson({ error, ...(message ? { message } : {}) }, { status });
}
