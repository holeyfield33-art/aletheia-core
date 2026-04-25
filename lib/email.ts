import { Resend } from "resend";
import { PRODUCT, URLS } from "@/lib/site-config";
import crypto from "crypto";
import prisma from "@/lib/prisma";

const resend = process.env.RESEND_API_KEY
  ? new Resend(process.env.RESEND_API_KEY)
  : null;

const FROM_ADDRESS =
  process.env.EMAIL_FROM || `${PRODUCT.name} <noreply@aletheia-core.com>`;

/**
 * Generate a verification token, store it in the DB, and send an email.
 * Falls back to auto-verify when RESEND_API_KEY is not set (dev mode).
 */
export async function sendVerificationEmail(email: string): Promise<boolean> {
  const token = crypto.randomBytes(32).toString("hex");
  const expires = new Date(Date.now() + 24 * 60 * 60 * 1000); // 24 hours

  // Store token in NextAuth VerificationToken table
  await prisma.verificationToken.create({
    data: {
      identifier: email,
      token,
      expires,
    },
  });

  const verifyUrl = `${URLS.appBase}/api/auth/verify-email?token=${token}&email=${encodeURIComponent(email)}`;

  if (!resend) {
    // Production must never auto-verify. If RESEND_API_KEY is missing here,
    // fail loudly so registration returns 500 and the operator notices —
    // the previous behavior silently marked any new account as verified,
    // letting an attacker register arbitrary emails as their own.
    if (process.env.NODE_ENV === "production") {
      console.error(
        "[email] RESEND_API_KEY is not set in production. Refusing to auto-verify.",
      );
      throw new Error("email_service_unconfigured");
    }
    // Dev/test only: log the link and auto-verify so local flow works.
    console.log(`[DEV] Verify: ${verifyUrl}`);
    await prisma.user.update({
      where: { email },
      data: { emailVerified: new Date() },
    });
    return true;
  }

  try {
    await resend.emails.send({
      from: FROM_ADDRESS,
      to: email,
      subject: `Verify your ${PRODUCT.name} account`,
      html: `
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 480px; margin: 0 auto; padding: 2rem;">
          <h2 style="color: #f0eee8; font-size: 1.25rem;">${PRODUCT.name}</h2>
          <p style="color: #A8B0B8; font-size: 0.95rem; line-height: 1.6;">
            Verify your email address to activate your account. This link expires in 24 hours.
          </p>
          <a href="${verifyUrl}" style="display: inline-block; background: #B02236; color: #f0eee8; padding: 0.75rem 1.5rem; border-radius: 6px; text-decoration: none; font-weight: 600; margin: 1rem 0;">
            Verify Email Address
          </a>
          <p style="color: #6b7585; font-size: 0.82rem; margin-top: 1.5rem;">
            If you didn't create an account, you can safely ignore this email.
          </p>
        </div>
      `,
    });
    return true;
  } catch (err) {
    console.error("Failed to send verification email:", err);
    return false;
  }
}
