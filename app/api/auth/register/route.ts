import { NextRequest, NextResponse } from "next/server";
import bcrypt from "bcryptjs";
import prisma from "@/lib/prisma";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MIN_PASSWORD_LENGTH = 8;
const MAX_NAME_LENGTH = 64;
const MAX_EMAIL_LENGTH = 255;

// In-memory rate limiter for registration (per IP, 5 attempts per hour)
const registerAttempts = new Map<string, { count: number; resetAt: number }>();
const REGISTER_LIMIT = 5;
const REGISTER_WINDOW_MS = 60 * 60 * 1000; // 1 hour

function checkRegisterRateLimit(ip: string): boolean {
  const now = Date.now();
  const entry = registerAttempts.get(ip);
  if (!entry || now > entry.resetAt) {
    registerAttempts.set(ip, { count: 1, resetAt: now + REGISTER_WINDOW_MS });
    return true;
  }
  if (entry.count >= REGISTER_LIMIT) return false;
  entry.count++;
  return true;
}

// Evict stale entries periodically (cap at 10k)
setInterval(() => {
  const now = Date.now();
  if (registerAttempts.size > 10000) {
    registerAttempts.forEach((val, key) => {
      if (now > val.resetAt) registerAttempts.delete(key);
    });
  }
}, 60_000);

export async function POST(request: NextRequest) {
  // Rate limit by IP
  const clientIp = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "unknown";
  if (!checkRegisterRateLimit(clientIp)) {
    return NextResponse.json(
      { error: "rate_limited", message: "Too many registration attempts. Try again later." },
      { status: 429, headers: { "Retry-After": "3600" } },
    );
  }

  try {
    const body = await request.json();
    const { name, email, password, tosAccepted } = body;

    // --- Validate TOS acceptance ---
    if (tosAccepted !== true) {
      return NextResponse.json(
        { error: "tos_required", message: "You must agree to the Terms of Service and Privacy Policy." },
        { status: 400 },
      );
    }

    // --- Validate inputs ---
    if (!email || typeof email !== "string" || !EMAIL_RE.test(email)) {
      return NextResponse.json(
        { error: "invalid_email", message: "A valid email address is required." },
        { status: 400 },
      );
    }
    if (email.length > MAX_EMAIL_LENGTH) {
      return NextResponse.json(
        { error: "invalid_email", message: "Email address is too long." },
        { status: 400 },
      );
    }
    if (!password || typeof password !== "string" || password.length < MIN_PASSWORD_LENGTH) {
      return NextResponse.json(
        { error: "weak_password", message: `Password must be at least ${MIN_PASSWORD_LENGTH} characters.` },
        { status: 400 },
      );
    }
    if (password.length > 128) {
      return NextResponse.json(
        { error: "invalid_password", message: "Password is too long." },
        { status: 400 },
      );
    }
    const safeName = typeof name === "string" ? name.slice(0, MAX_NAME_LENGTH).trim() : null;

    const normalizedEmail = email.toLowerCase().trim();

    // --- Check for existing user ---
    const existing = await prisma.user.findUnique({
      where: { email: normalizedEmail },
    });
    if (existing) {
      return NextResponse.json(
        { error: "registration_failed", message: "Unable to create account. If you already have an account, please sign in." },
        { status: 400 },
      );
    }

    // --- Hash password ---
    const hashedPassword = await bcrypt.hash(password, 12);

    // --- Create user ---
    const user = await prisma.user.create({
      data: {
        name: safeName,
        email: normalizedEmail,
        password: hashedPassword,
        emailVerified: new Date(), // Auto-verify for now; add email flow later
        role: "USER",
        plan: "TRIAL",
        tosAcceptedAt: new Date(),
      },
    });

    return NextResponse.json(
      {
        success: true,
        message: "Account created successfully. You can now sign in.",
        userId: user.id,
      },
      { status: 201 },
    );
  } catch (err) {
    console.error("Registration error:", err);
    return NextResponse.json(
      { error: "internal_error", message: "An unexpected error occurred." },
      { status: 500 },
    );
  }
}
