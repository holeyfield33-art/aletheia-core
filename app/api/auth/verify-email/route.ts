import { NextRequest, NextResponse } from "next/server";
import prisma from "@/lib/prisma";

export async function GET(request: NextRequest) {
  const token = request.nextUrl.searchParams.get("token");
  const email = request.nextUrl.searchParams.get("email");

  if (!token || !email) {
    return NextResponse.redirect(
      new URL("/auth/error?error=MissingToken", request.url),
    );
  }

  try {
    // Look up the token
    const record = await prisma.verificationToken.findFirst({
      where: { identifier: email, token },
    });

    if (!record) {
      return NextResponse.redirect(
        new URL("/auth/error?error=InvalidToken", request.url),
      );
    }

    // Check expiry
    if (record.expires < new Date()) {
      // Clean up expired token
      await prisma.verificationToken.delete({
        where: { identifier_token: { identifier: email, token } },
      });
      return NextResponse.redirect(
        new URL("/auth/error?error=TokenExpired", request.url),
      );
    }

    // Mark user as verified — use the token record's identifier (authoritative),
    // NOT the query-param email, to prevent parameter-substitution attacks.
    await prisma.user.update({
      where: { email: record.identifier },
      data: { emailVerified: new Date() },
    });

    // Delete consumed token
    await prisma.verificationToken.delete({
      where: { identifier_token: { identifier: email, token } },
    });

    // Redirect to login with success
    return NextResponse.redirect(
      new URL("/auth/login?verified=true", request.url),
    );
  } catch (err) {
    console.error("Email verification error:", err);
    return NextResponse.redirect(
      new URL("/auth/error?error=VerificationFailed", request.url),
    );
  }
}
