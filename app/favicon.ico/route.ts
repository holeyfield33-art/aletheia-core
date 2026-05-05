import { NextResponse } from "next/server";

const FAVICON_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <rect width="32" height="32" rx="6" fill="#b02236" />
  <path d="M16 7l7 18h-3.7l-1.5-4h-7.6l-1.5 4H5L12 7h4zm0 5.1l-2.4 6.2h4.8L16 12.1z" fill="#ffffff"/>
</svg>`;

export const runtime = "edge";

export function GET() {
  return new NextResponse(FAVICON_SVG, {
    status: 200,
    headers: {
      "Content-Type": "image/svg+xml",
      "Cache-Control": "public, max-age=86400, stale-while-revalidate=86400",
      "X-Content-Type-Options": "nosniff",
    },
  });
}
