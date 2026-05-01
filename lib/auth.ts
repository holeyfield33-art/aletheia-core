import { NextAuthOptions } from "next-auth";
import type { JWT } from "next-auth/jwt";
import { PrismaAdapter } from "@auth/prisma-adapter";
import CredentialsProvider from "next-auth/providers/credentials";
import GitHubProvider from "next-auth/providers/github";
import GoogleProvider from "next-auth/providers/google";
import bcrypt from "bcryptjs";
import prisma from "@/lib/prisma";
import { consumeRateLimit } from "@/lib/rate-limit";

// Distributed login attempt tracking via Prisma (PostgreSQL).
// Replaces the previous in-memory Map so brute-force protection
// works across all server instances.
const LOGIN_FAIL_LIMIT = 5;
const LOGIN_WINDOW_MS = 15 * 60 * 1000; // 15 minutes
const LOGIN_IP_LIMIT = 20;
const LOGIN_IP_WINDOW_MS = 15 * 60 * 1000; // 15 minutes
// JWT claims (role, plan, deletedAt) are re-fetched at most this often.
// Lower = stronger revocation guarantee for deleted/role-changed users at
// the cost of one DB round-trip per active user per interval.
// Tunable via env to absorb load spikes without a redeploy.
const CLAIM_REFRESH_MS = (() => {
  const fromEnv = parseInt(process.env.AUTH_CLAIM_REFRESH_MS ?? "", 10);
  if (Number.isFinite(fromEnv) && fromEnv >= 10_000) return fromEnv;
  return 60_000; // 60s default (was 15m — too wide for deleted-user revocation)
})();

type AppToken = JWT & {
  id?: string;
  role?: string;
  plan?: string;
  claimsRefreshedAt?: number;
  deletedAt?: string | null;
};

async function checkLoginRateLimit(email: string): Promise<boolean> {
  const windowStart = new Date(Date.now() - LOGIN_WINDOW_MS);
  const count = await prisma.loginAttempt.count({
    where: { email, createdAt: { gte: windowStart } },
  });
  return count < LOGIN_FAIL_LIMIT;
}

function getHeaderValue(headers: unknown, headerName: string): string | null {
  if (!headers) return null;
  if (headers instanceof Headers) {
    return headers.get(headerName);
  }

  if (typeof headers === "object") {
    const key = Object.keys(headers as Record<string, unknown>).find(
      (k) => k.toLowerCase() === headerName.toLowerCase(),
    );
    if (!key) return null;
    const value = (headers as Record<string, unknown>)[key];
    if (typeof value === "string") return value;
    if (Array.isArray(value)) return String(value[0] ?? "");
  }

  return null;
}

export function extractClientIp(headers: unknown): string | null {
  const forwardedFor = getHeaderValue(headers, "x-forwarded-for");
  if (forwardedFor) {
    const first = forwardedFor.split(",")[0]?.trim();
    if (first) return first;
  }

  const realIp = getHeaderValue(headers, "x-real-ip")?.trim();
  if (realIp) return realIp;

  return null;
}

export async function consumeLoginIpRateLimit(ip: string): Promise<boolean> {
  const result = await consumeRateLimit({
    action: "auth_login_ip",
    key: ip,
    limit: LOGIN_IP_LIMIT,
    windowMs: LOGIN_IP_WINDOW_MS,
  });
  return result.allowed;
}

async function recordLoginFailure(email: string): Promise<void> {
  await prisma.loginAttempt.create({ data: { email } });
}

async function clearLoginFailures(email: string): Promise<void> {
  await prisma.loginAttempt.deleteMany({ where: { email } });
}

async function refreshTokenClaims(token: AppToken): Promise<AppToken> {
  if (!token.id) return token;

  const user = await prisma.user.findUnique({
    where: { id: token.id },
    select: {
      role: true,
      plan: true,
      deletedAt: true,
      name: true,
      email: true,
      image: true,
    },
  });

  if (!user || user.deletedAt) {
    return {
      ...token,
      deletedAt: user?.deletedAt?.toISOString() ?? new Date().toISOString(),
      claimsRefreshedAt: Date.now(),
    };
  }

  return {
    ...token,
    role: user.role,
    plan: user.plan,
    deletedAt: null,
    name: user.name ?? token.name,
    email: user.email ?? token.email,
    picture: user.image ?? token.picture,
    claimsRefreshedAt: Date.now(),
  };
}

/**
 * Pure resolver for the next-auth `redirect` callback. Exported for unit
 * tests so the open-redirect contract is regression-locked. Behavior:
 *   - protocol-relative URLs (`//evil`) return `baseUrl`
 *   - relative paths are appended to `baseUrl` after decode + traversal check
 *   - absolute URLs are accepted only when origin === baseUrl origin
 *   - everything else returns `baseUrl`
 */
export function resolveAuthRedirect(url: string, baseUrl: string): string {
  if (!url || typeof url !== "string") return baseUrl;
  if (url.startsWith("//")) return baseUrl;
  if (url.startsWith("/")) {
    const decoded = decodeURIComponent(url);
    if (decoded.includes("//") || decoded.includes("\\")) return baseUrl;
    return `${baseUrl}${decoded}`;
  }
  try {
    const target = new URL(url);
    const base = new URL(baseUrl);
    if (target.origin === base.origin) return url;
  } catch {
    // unparseable — fall through
  }
  return baseUrl;
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
      async authorize(credentials, req) {
        if (!credentials?.email || !credentials?.password) return null;

        const email = credentials.email.toLowerCase().trim();
        const clientIp = extractClientIp(req?.headers);

        if (clientIp && !(await consumeLoginIpRateLimit(clientIp))) {
          return null;
        }

        // Brute-force protection: block after 5 failed attempts in 15 min
        if (!(await checkLoginRateLimit(email))) return null;

        const user = await prisma.user.findUnique({
          where: { email },
        });
        if (!user?.password) {
          await recordLoginFailure(email);
          return null;
        }

        // Reject soft-deleted accounts
        if ((user as { deletedAt?: Date | null }).deletedAt) return null;

        const valid = await bcrypt.compare(credentials.password, user.password);
        if (!valid) {
          await recordLoginFailure(email);
          return null;
        }

        if (!user.emailVerified) {
          // Keep timing and failure accounting aligned with wrong-password flow.
          await bcrypt.compare(credentials.password, user.password);
          await recordLoginFailure(email);
          return null;
        }

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
      return resolveAuthRedirect(url, baseUrl);
    },
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id;
        token.role = user.role ?? "USER";
        token.plan = user.plan ?? "TRIAL";
        token.deletedAt = null;
        token.claimsRefreshedAt = Date.now();
        return token;
      }

      const appToken = token as AppToken;
      const lastRefresh = appToken.claimsRefreshedAt ?? 0;
      if (appToken.id && Date.now() - lastRefresh >= CLAIM_REFRESH_MS) {
        return refreshTokenClaims(appToken);
      }

      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.id = token.deletedAt ? "" : token.id;
        session.user.name = token.name ?? session.user.name;
        session.user.email = token.email ?? session.user.email;
        session.user.image = token.picture ?? session.user.image;
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
  // Only trust Host on Vercel-managed deployments where the proxy chain is known.
  ...(process.env.VERCEL ? { trustHost: true } : {}),
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
      "Generate with: openssl rand -base64 32",
  );
}
