import { NextRequest, NextResponse } from "next/server";
import { isIP } from "node:net";
import bcrypt from "bcryptjs";
import prisma from "@/lib/prisma";
import { sendVerificationEmail } from "@/lib/email";
import { consumeRateLimit } from "@/lib/rate-limit";
import { normalizeEmail, upsertUserProfile } from "@/lib/auth/profile";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MIN_PASSWORD_LENGTH = 8;
const MAX_NAME_LENGTH = 64;
const MAX_EMAIL_LENGTH = 255;

// 2026 baseline for bcrypt; do not lower without security review.
const BCRYPT_COST = 14;

const REGISTER_LIMIT = 5;
const REGISTER_WINDOW_MS = 60 * 60 * 1000; // 1 hour

// Only honor cf-connecting-ip when we are actually deployed behind Cloudflare.
// Otherwise an attacker can rotate this header to bypass per-IP rate limits.
const TRUST_CF_HEADERS = process.env.TRUST_CF_HEADERS === "true";

function extractClientIp(request: NextRequest): string {
  if (TRUST_CF_HEADERS) {
    const cloudflareIp = request.headers.get("cf-connecting-ip")?.trim();
    if (cloudflareIp && isIP(cloudflareIp)) return cloudflareIp;
  }

  const forwardedFor = request.headers.get("x-forwarded-for");
  if (forwardedFor) {
    const candidate = forwardedFor
      .split(",")
      .map((value) => value.trim())
      .reverse()
      .find((value) => isIP(value));
    if (candidate) return candidate;
  }

  return "unknown";
}

export async function POST(request: NextRequest) {
  const clientIp = extractClientIp(request);
  const rateLimit = await consumeRateLimit({
    action: "register",
    key: clientIp,
    limit: REGISTER_LIMIT,
    windowMs: REGISTER_WINDOW_MS,
  });

  if (!rateLimit.allowed) {
    return NextResponse.json(
      {
        error: "rate_limited",
        message: "Too many registration attempts. Try again later.",
      },
      {
        status: 429,
        headers: { "Retry-After": String(rateLimit.retryAfterSeconds) },
      },
    );
  }

  try {
    const body = await request.json();
    const { name, email, password, tosAccepted } = body;

    // --- Validate TOS acceptance ---
    if (tosAccepted !== true) {
      return NextResponse.json(
        {
          error: "tos_required",
          message: "You must agree to the Terms of Service and Privacy Policy.",
        },
        { status: 400 },
      );
    }

    // --- Validate inputs ---
    if (!email || typeof email !== "string" || !EMAIL_RE.test(email)) {
      return NextResponse.json(
        {
          error: "invalid_email",
          message: "A valid email address is required.",
        },
        { status: 400 },
      );
    }
    if (email.length > MAX_EMAIL_LENGTH) {
      return NextResponse.json(
        { error: "invalid_email", message: "Email address is too long." },
        { status: 400 },
      );
    }
    if (
      !password ||
      typeof password !== "string" ||
      password.length < MIN_PASSWORD_LENGTH
    ) {
      return NextResponse.json(
        {
          error: "weak_password",
          message: `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`,
        },
        { status: 400 },
      );
    }
    if (password.length > 128) {
      return NextResponse.json(
        { error: "invalid_password", message: "Password is too long." },
        { status: 400 },
      );
    }
    const safeName =
      typeof name === "string" ? name.slice(0, MAX_NAME_LENGTH).trim() : null;

    const normalizedEmail = normalizeEmail(email);

    // --- Check for existing user ---
    const existing = await prisma.user.findUnique({
      where: { email: normalizedEmail },
    });
    if (existing) {
      return NextResponse.json(
        {
          error: "registration_failed",
          message: "An account already exists with this email. Sign in instead.",
        },
        { status: 400 },
      );
    }

    // --- Hash password ---
    const hashedPassword = await bcrypt.hash(password, BCRYPT_COST);

    // --- Create user ---
    const user = await prisma.user.create({
      data: {
        name: safeName,
        email: normalizedEmail,
        password: hashedPassword,
        // emailVerified left null — set when user clicks verification link
        role: "USER",
        plan: "TRIAL",
        tosAcceptedAt: new Date(),
      },
    });

    await upsertUserProfile({
      userId: user.id,
      email: normalizedEmail,
      fullName: safeName,
    });

    // --- Send verification email ---
    // If the email service is unconfigured in production, sendVerificationEmail
    // throws — roll back the user record so we don't leave an unreachable
    // account behind, and surface a clear configuration error.
    try {
      await sendVerificationEmail(normalizedEmail);
    } catch (emailErr) {
      await prisma.user
        .delete({ where: { id: user.id } })
        .catch(() => undefined);
      const message = emailErr instanceof Error ? emailErr.message : "unknown";
      if (message === "email_service_unconfigured") {
        return NextResponse.json(
          {
            error: "email_service_unconfigured",
            message:
              "Account creation is temporarily unavailable. Please try again later.",
          },
          { status: 503 },
        );
      }
      throw emailErr;
    }

    return NextResponse.json(
      {
        success: true,
        message:
          "Account created. Please check your email to verify your address.",
        userId: user.id,
        requiresVerification: true,
      },
      { status: 201 },
    );
  } catch (err) {
    console.error(
      "[register]",
      err instanceof Error ? err.message : "unknown error",
    );
    return NextResponse.json(
      { error: "internal_error", message: "An unexpected error occurred." },
      { status: 500 },
    );
  }
}
