import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { redirect } from "next/navigation";

/**
 * Server-side helper: get the current session or redirect to login.
 * Use in server components and API routes that require authentication.
 */
export async function requireAuth() {
  try {
    const session = await getServerSession(authOptions);
    if (!session?.user?.id) {
      redirect("/auth/login");
    }
    return session;
  } catch (err: unknown) {
    // Re-throw Next.js redirect (it throws a special NEXT_REDIRECT error)
    if (err instanceof Error && "digest" in err) throw err;
    // Auth misconfiguration (missing NEXTAUTH_SECRET, bad DB, etc.) — redirect safely
    console.error("[requireAuth] session check failed:", err);
    redirect("/auth/login");
  }
}

/**
 * Server-side helper: get session without redirecting.
 */
export async function getAuth() {
  try {
    return await getServerSession(authOptions);
  } catch (err) {
    console.error("[getAuth] session check failed:", err);
    return null;
  }
}
