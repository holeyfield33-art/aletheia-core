import { NextRequest, NextResponse } from "next/server";
import bcrypt from "bcryptjs";
import prisma from "@/lib/prisma";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MIN_PASSWORD_LENGTH = 8;
const MAX_NAME_LENGTH = 64;
const MAX_EMAIL_LENGTH = 255;

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { name, email, password } = body;

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
        { error: "email_taken", message: "An account with this email already exists. Please sign in instead." },
        { status: 409 },
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
