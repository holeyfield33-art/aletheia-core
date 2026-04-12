import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { redirect } from "next/navigation";

/**
 * Server-side helper: get the current session or redirect to login.
 * Use in server components and API routes that require authentication.
 */
export async function requireAuth() {
  const session = await getServerSession(authOptions);
  if (!session?.user?.id) {
    redirect("/auth/login");
  }
  return session;
}

/**
 * Server-side helper: get session without redirecting.
 */
export async function getAuth() {
  return getServerSession(authOptions);
}
