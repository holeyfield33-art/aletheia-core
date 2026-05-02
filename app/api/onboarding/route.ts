import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import prisma from "@/lib/prisma";
import {
  ONBOARDING_RISK_OPTIONS,
  ONBOARDING_TOOL_OPTIONS,
  ONBOARDING_USE_CASE_OPTIONS,
  serializeToolAccessProfile,
} from "@/lib/onboarding";
import { normalizeEmail } from "@/lib/auth/profile";

function isAllowedOption<T extends readonly string[]>(
  value: string,
  options: T,
): value is T[number] {
  return options.includes(value as T[number]);
}

export async function GET() {
  const session = await getServerSession(authOptions);
  if (!session?.user?.id || !session.user.email) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const profile = await prisma.userProfile.findUnique({
    where: { userId: session.user.id },
  });

  return NextResponse.json({ profile });
}

export async function POST(request: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session?.user?.id || !session.user.email) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const body = await request.json();
  const useCase = typeof body.useCase === "string" ? body.useCase.trim() : "";
  const primaryGoal =
    typeof body.primaryGoal === "string" ? body.primaryGoal.trim() : "";
  const fullName =
    typeof body.fullName === "string" ? body.fullName.trim() : session.user.name;
  const companyName =
    typeof body.companyName === "string" ? body.companyName.trim() : null;
  const role = typeof body.role === "string" ? body.role.trim() : null;
  const handlesSensitiveData = body.handlesSensitiveData === true;
  const agentTypes = Array.isArray(body.agentTypes)
    ? body.agentTypes.filter(
        (entry: unknown): entry is string => typeof entry === "string",
      )
    : [];

  if (!isAllowedOption(useCase, ONBOARDING_USE_CASE_OPTIONS)) {
    return NextResponse.json({ error: "invalid_use_case" }, { status: 400 });
  }

  if (!isAllowedOption(primaryGoal, ONBOARDING_RISK_OPTIONS)) {
    return NextResponse.json({ error: "invalid_primary_goal" }, { status: 400 });
  }

  if (
    agentTypes.length === 0 ||
    agentTypes.some(
      (entry: string) => !isAllowedOption(entry, ONBOARDING_TOOL_OPTIONS),
    )
  ) {
    return NextResponse.json({ error: "invalid_agent_types" }, { status: 400 });
  }

  const hasToolAccess = !agentTypes.includes("No tools yet");
  const normalizedEmail = normalizeEmail(session.user.email);

  const profile = await prisma.userProfile.upsert({
    where: { userId: session.user.id },
    update: {
      email: normalizedEmail,
      fullName: fullName ?? undefined,
      companyName,
      role,
      useCase,
      agentType: serializeToolAccessProfile(agentTypes),
      hasToolAccess,
      handlesSensitiveData,
      primaryGoal,
      onboardingCompleted: true,
    },
    create: {
      userId: session.user.id,
      email: normalizedEmail,
      fullName: fullName ?? undefined,
      companyName,
      role,
      useCase,
      agentType: serializeToolAccessProfile(agentTypes),
      hasToolAccess,
      handlesSensitiveData,
      primaryGoal,
      onboardingCompleted: true,
    },
  });

  return NextResponse.json({ success: true, profile });
}
