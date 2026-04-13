import type { Metadata } from "next";
import { requireAuth } from "@/lib/server-auth";
import prisma from "@/lib/prisma";
import SettingsClient from "./SettingsClient";

export const metadata: Metadata = {
  title: "Settings",
};

export default async function SettingsPage() {
  const session = await requireAuth();
  const userId = session.user.id;

  let createdAt = "";
  let hasPassword = false;
  try {
    const user = await prisma.user.findUnique({
      where: { id: userId },
      select: { createdAt: true, password: true },
    });
    if (user?.createdAt) {
      createdAt = user.createdAt.toLocaleDateString("en-US", {
        year: "numeric",
        month: "long",
        day: "numeric",
      });
    }
    hasPassword = !!user?.password;
  } catch {
    createdAt = "—";
  }

  return (
    <SettingsClient
      name={session.user.name ?? null}
      email={session.user.email ?? null}
      plan={session.user.plan}
      createdAt={createdAt}
      hasPassword={hasPassword}
    />
  );
}
