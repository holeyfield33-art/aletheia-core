import { Prisma } from "@prisma/client";
import prisma from "@/lib/prisma";

type ConsumeRateLimitInput = {
  action: string;
  key: string;
  limit: number;
  windowMs: number;
  pruneAfterMs?: number;
};

type ConsumeRateLimitResult = {
  allowed: boolean;
  retryAfterSeconds: number;
  remaining: number;
};

const DEFAULT_PRUNE_MULTIPLIER = 7;
const SERIALIZATION_RETRY_LIMIT = 2;

function isRetryablePrismaError(error: unknown): boolean {
  return (
    error instanceof Prisma.PrismaClientKnownRequestError &&
    error.code === "P2034"
  );
}

export async function consumeRateLimit(
  input: ConsumeRateLimitInput,
): Promise<ConsumeRateLimitResult> {
  const pruneAfterMs =
    input.pruneAfterMs ?? input.windowMs * DEFAULT_PRUNE_MULTIPLIER;

  for (let attempt = 0; attempt <= SERIALIZATION_RETRY_LIMIT; attempt++) {
    try {
      return await prisma.$transaction(
        async (tx) => {
          const now = Date.now();
          const windowStart = new Date(now - input.windowMs);
          const pruneBefore = new Date(now - pruneAfterMs);

          await tx.rateLimitEvent.deleteMany({
            where: {
              action: input.action,
              key: input.key,
              createdAt: { lt: pruneBefore },
            },
          });

          const recent = await tx.rateLimitEvent.findMany({
            where: {
              action: input.action,
              key: input.key,
              createdAt: { gte: windowStart },
            },
            orderBy: { createdAt: "asc" },
            select: { createdAt: true },
            take: input.limit,
          });

          if (recent.length >= input.limit) {
            const oldest = recent[0]?.createdAt;
            const retryAfterSeconds = oldest
              ? Math.max(
                  1,
                  Math.ceil((input.windowMs - (now - oldest.getTime())) / 1000),
                )
              : Math.max(1, Math.ceil(input.windowMs / 1000));

            return {
              allowed: false,
              retryAfterSeconds,
              remaining: 0,
            };
          }

          await tx.rateLimitEvent.create({
            data: {
              action: input.action,
              key: input.key,
            },
          });

          return {
            allowed: true,
            retryAfterSeconds: 0,
            remaining: Math.max(0, input.limit - recent.length - 1),
          };
        },
        { isolationLevel: Prisma.TransactionIsolationLevel.Serializable },
      );
    } catch (error) {
      if (
        !isRetryablePrismaError(error) ||
        attempt === SERIALIZATION_RETRY_LIMIT
      ) {
        throw error;
      }
    }
  }

  throw new Error("rate limit transaction failed");
}
