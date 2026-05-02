import prisma from "@/lib/prisma";

export function normalizeEmail(email: string): string {
  return email.trim().toLowerCase();
}

type UpsertProfileInput = {
  userId: string;
  email: string;
  fullName?: string | null;
};

export async function upsertUserProfile({
  userId,
  email,
  fullName,
}: UpsertProfileInput) {
  const normalizedEmail = normalizeEmail(email);

  return prisma.userProfile.upsert({
    where: { userId },
    update: {
      email: normalizedEmail,
      fullName: fullName ?? undefined,
    },
    create: {
      userId,
      email: normalizedEmail,
      fullName: fullName ?? undefined,
    },
  });
}

export async function findProfileByUserId(userId: string) {
  return prisma.userProfile.findUnique({
    where: { userId },
  });
}
