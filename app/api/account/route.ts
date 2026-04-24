import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { getToken } from "next-auth/jwt";
import { authOptions } from "@/lib/auth";
import prisma from "@/lib/prisma";
import bcrypt from "bcryptjs";

const OAUTH_DELETE_REAUTH_WINDOW_SECONDS = 10 * 60;

export async function DELETE(request: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session?.user?.email) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const body = await request.json().catch(() => null);
  const confirmationPassword = body?.password;
  const confirmationEmail = typeof body?.confirmEmail === "string"
    ? body.confirmEmail.trim().toLowerCase()
    : "";

  const user = await prisma.user.findUnique({
    where: { email: session.user.email },
    select: { id: true, password: true, email: true },
  });

  if (!user) {
    return NextResponse.json({ error: "not_found" }, { status: 404 });
  }

  // If user has a password (credentials-based), require confirmation
  if (user.password) {
    if (!confirmationPassword || typeof confirmationPassword !== "string") {
      return NextResponse.json(
        { error: "password_required", message: "Please confirm your password to delete your account." },
        { status: 400 },
      );
    }
    const valid = await bcrypt.compare(confirmationPassword, user.password);
    if (!valid) {
      return NextResponse.json(
        { error: "invalid_password", message: "Incorrect password." },
        { status: 403 },
      );
    }
  } else {
    if (!user.email || confirmationEmail !== user.email.toLowerCase()) {
      return NextResponse.json(
        {
          error: "email_confirmation_required",
          message: "Type your email address exactly to confirm account deletion.",
        },
        { status: 400 },
      );
    }

    const token = await getToken({
      req: request,
      secret: process.env.NEXTAUTH_SECRET,
    });
    const issuedAt = typeof token?.iat === "number" ? token.iat : 0;
    const ageSeconds = issuedAt > 0 ? Math.floor(Date.now() / 1000) - issuedAt : Infinity;

    if (ageSeconds > OAUTH_DELETE_REAUTH_WINDOW_SECONDS) {
      return NextResponse.json(
        {
          error: "reauth_required",
          message: "Please sign out and sign back in before deleting an OAuth account.",
        },
        { status: 403 },
      );
    }
  }

  // Soft-delete: set deletedAt, revoke all API keys, clear sessions
  await prisma.$transaction([
    prisma.user.update({
      where: { id: user.id },
      data: { deletedAt: new Date() },
    }),
    prisma.apiKey.updateMany({
      where: { userId: user.id, status: "active" },
      data: { status: "revoked" },
    }),
    prisma.session.deleteMany({
      where: { userId: user.id },
    }),
  ]);

  return NextResponse.json(
    { success: true, message: "Account scheduled for deletion. You have been signed out." },
    { status: 200 },
  );
}
