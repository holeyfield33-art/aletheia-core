import { NextAuthOptions } from "next-auth";
import { PrismaAdapter } from "@auth/prisma-adapter";
import CredentialsProvider from "next-auth/providers/credentials";
import GitHubProvider from "next-auth/providers/github";
import GoogleProvider from "next-auth/providers/google";
import bcrypt from "bcryptjs";
import prisma from "@/lib/prisma";
import { getBaseUrl } from "@/lib/auth-config";

// Distributed login attempt tracking via Prisma (PostgreSQL).
// Replaces the previous in-memory Map so brute-force protection
// works across all server instances.
const LOGIN_FAIL_LIMIT = 5;
const LOGIN_WINDOW_MS = 15 * 60 * 1000; // 15 minutes

async function checkLoginRateLimit(email: string): Promise<boolean> {
  const windowStart = new Date(Date.now() - LOGIN_WINDOW_MS);
  const count = await prisma.loginAttempt.count({
    where: { email, createdAt: { gte: windowStart } },
  });
  return count < LOGIN_FAIL_LIMIT;
}

async function recordLoginFailure(email: string): Promise<void> {
  await prisma.loginAttempt.create({ data: { email } });
}

async function clearLoginFailures(email: string): Promise<void> {
  await prisma.loginAttempt.deleteMany({ where: { email } });
}

// Periodic cleanup of expired attempts (runs every 60s, deletes rows older than window)
setInterval(async () => {
  try {
    const cutoff = new Date(Date.now() - LOGIN_WINDOW_MS);
    await prisma.loginAttempt.deleteMany({
      where: { createdAt: { lt: cutoff } },
    });
  } catch {
    // Silently ignore cleanup errors — stale rows are harmless
  }
}, 60_000);

export const authOptions: NextAuthOptions = {
  adapter: PrismaAdapter(prisma) as NextAuthOptions["adapter"],
  providers: [
    // --- Email / Password ---
    CredentialsProvider({
      name: "credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null;

        const email = credentials.email.toLowerCase().trim();

        // Brute-force protection: block after 5 failed attempts in 15 min
        if (!(await checkLoginRateLimit(email))) return null;

        const user = await prisma.user.findUnique({
          where: { email },
        });
        if (!user?.password) {
          await recordLoginFailure(email);
          return null;
        }

        const valid = await bcrypt.compare(credentials.password, user.password);
        if (!valid) {
          await recordLoginFailure(email);
          return null;
        }

        if (!user.emailVerified) return null;

        await clearLoginFailures(email);

        return {
          id: user.id,
          email: user.email,
          name: user.name,
          image: user.image,
          role: user.role,
          plan: user.plan,
        };
      },
    }),
    // --- GitHub OAuth ---
    ...(process.env.GITHUB_CLIENT_ID && process.env.GITHUB_CLIENT_SECRET
      ? [
          GitHubProvider({
            clientId: process.env.GITHUB_CLIENT_ID,
            clientSecret: process.env.GITHUB_CLIENT_SECRET,
          }),
        ]
      : []),
    // --- Google OAuth ---
    ...(process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET
      ? [
          GoogleProvider({
            clientId: process.env.GOOGLE_CLIENT_ID,
            clientSecret: process.env.GOOGLE_CLIENT_SECRET,
          }),
        ]
      : []),
  ],
  session: {
    strategy: "jwt",
    maxAge: 7 * 24 * 60 * 60, // 7 days (reduced from 30 for security)
  },
  pages: {
    signIn: "/auth/login",
    newUser: "/dashboard",
    error: "/auth/error",
  },
  callbacks: {
    async redirect({ url, baseUrl }) {
      if (!url || typeof url !== "string") return baseUrl;
      // Block protocol-relative redirects (//evil.com)
      if (url.startsWith("//")) return baseUrl;
      // Allow relative paths (no traversal)
      if (url.startsWith("/")) {
        const decoded = decodeURIComponent(url);
        if (decoded.includes("//") || decoded.includes("\\")) return baseUrl;
        return `${baseUrl}${decoded}`;
      }
      // Allow same-origin absolute URLs only
      if (url.startsWith(baseUrl)) return url;
      return baseUrl;
    },
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id;
        token.role = user.role ?? "USER";
        token.plan = user.plan ?? "TRIAL";
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.id = token.id;
        session.user.role = token.role;
        session.user.plan = token.plan;
      }
      return session;
    },
  },
  events: {
    async createUser({ user }) {
      // Auto-verify OAuth users (they already verified with provider)
      if (user.email) {
        const dbUser = await prisma.user.findUnique({ where: { id: user.id } });
        if (dbUser && !dbUser.emailVerified) {
          await prisma.user.update({
            where: { id: user.id },
            data: { emailVerified: new Date() },
          });
        }
      }
    },
  },
  secret: process.env.NEXTAUTH_SECRET,
  // Trust the Host header on Vercel (behind proxy/load balancer)
  // Also enable via AUTH_TRUST_HOST=true env var
  ...(process.env.VERCEL || process.env.AUTH_TRUST_HOST === "true"
    ? { trustHost: true }
    : {}),
};

// Runtime guard: refuse to start with a weak NEXTAUTH_SECRET in production
// Skip during build (next build sets NODE_ENV=production but NEXTAUTH_URL is absent)
if (
  process.env.NODE_ENV === "production" &&
  process.env.NEXTAUTH_URL &&
  (process.env.NEXTAUTH_SECRET || "").length < 32
) {
  throw new Error(
    "NEXTAUTH_SECRET must be at least 32 characters in production. " +
    "Generate with: openssl rand -base64 32"
  );
}
