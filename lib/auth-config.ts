import { APP_ORIGIN } from "@/lib/site-config";

/**
 * Dynamic base URL resolution for NextAuth callbacks and redirects.
 *
 * Priority:
 *   1. NEXTAUTH_URL (explicitly set — production only)
 *   2. VERCEL_URL   (auto-set by Vercel on every deployment, including previews)
 *   3. localhost     (local development fallback)
 *   4. Production fallback
 */
export function getBaseUrl(): string {
  if (process.env.NEXTAUTH_URL) return process.env.NEXTAUTH_URL;
  if (process.env.VERCEL_URL) return `https://${process.env.VERCEL_URL}`;
  if (process.env.NODE_ENV === "development") return "http://localhost:3000";
  return APP_ORIGIN;
}
