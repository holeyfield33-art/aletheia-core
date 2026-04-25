import prisma from "@/lib/prisma";

type PendingUsageRow = {
  userId: string;
  pendingUsage: bigint | number;
  stripeCustomerId: string | null;
  stripeSubscriptionId: string | null;
};

type MonthlyUsageRow = {
  usage: bigint | number | null;
};

type CountRow = {
  count: bigint | number;
};

let usageTablesInitPromise: Promise<void> | null = null;

function toNumber(value: bigint | number | null | undefined): number {
  if (typeof value === "bigint") return Number(value);
  return value ?? 0;
}

async function ensureUsageTables(): Promise<void> {
  if (usageTablesInitPromise) return usageTablesInitPromise;

  usageTablesInitPromise = (async () => {
    await prisma.$executeRawUnsafe(`
      CREATE TABLE IF NOT EXISTS user_usage (
        user_id TEXT PRIMARY KEY REFERENCES "User"(id) ON DELETE CASCADE,
        total_usage BIGINT NOT NULL DEFAULT 0,
        unreported_usage BIGINT NOT NULL DEFAULT 0,
        last_reported_at TIMESTAMP,
        pending_since TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
      )
    `);

    await prisma.$executeRawUnsafe(`
      CREATE TABLE IF NOT EXISTS usage_events (
        id BIGSERIAL PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES "User"(id) ON DELETE CASCADE,
        quantity INTEGER NOT NULL CHECK (quantity > 0),
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        reported_to_stripe BOOLEAN NOT NULL DEFAULT FALSE,
        reported_at TIMESTAMP
      )
    `);

    await prisma.$executeRawUnsafe(
      "CREATE INDEX IF NOT EXISTS idx_usage_events_user_reported_created ON usage_events(user_id, reported_to_stripe, created_at)",
    );
    await prisma.$executeRawUnsafe(
      "CREATE INDEX IF NOT EXISTS idx_user_usage_unreported ON user_usage(unreported_usage)",
    );
  })();

  return usageTablesInitPromise;
}

export async function incrementUsage(userId: string, quantity: number = 1): Promise<void> {
  if (!userId || quantity <= 0) return;
  await ensureUsageTables();

  await prisma.$transaction(async (tx) => {
    await tx.$executeRawUnsafe(
      `
      INSERT INTO user_usage (user_id, total_usage, unreported_usage, pending_since, updated_at)
      VALUES ($1, $2, $2, NOW(), NOW())
      ON CONFLICT (user_id)
      DO UPDATE SET
        total_usage = user_usage.total_usage + EXCLUDED.total_usage,
        unreported_usage = user_usage.unreported_usage + EXCLUDED.unreported_usage,
        pending_since = COALESCE(user_usage.pending_since, NOW()),
        updated_at = NOW()
      `,
      userId,
      quantity,
    );

    await tx.$executeRawUnsafe(
      "INSERT INTO usage_events (user_id, quantity) VALUES ($1, $2)",
      userId,
      quantity,
    );
  });
}

export async function getUnreportedUsage(userId: string): Promise<number> {
  if (!userId) return 0;
  await ensureUsageTables();

  const rows = await prisma.$queryRawUnsafe<Array<{ unreported_usage: bigint | number }>>(
    "SELECT unreported_usage FROM user_usage WHERE user_id = $1",
    userId,
  );

  return rows.length > 0 ? toNumber(rows[0].unreported_usage) : 0;
}

export async function clearUnreportedUsage(userId: string, amount: number): Promise<void> {
  if (!userId || amount <= 0) return;
  await ensureUsageTables();

  await prisma.$transaction(async (tx) => {
    await tx.$executeRawUnsafe(
      `
      WITH current_usage AS (
        SELECT unreported_usage
        FROM user_usage
        WHERE user_id = $1
        FOR UPDATE
      )
      UPDATE user_usage
      SET
        unreported_usage = GREATEST(0, user_usage.unreported_usage - $2),
        last_reported_at = NOW(),
        pending_since = CASE
          WHEN GREATEST(0, user_usage.unreported_usage - $2) = 0 THEN NULL
          ELSE user_usage.pending_since
        END,
        updated_at = NOW()
      WHERE user_id = $1
      `,
      userId,
      amount,
    );

    await tx.$executeRawUnsafe(
      `
      WITH ordered AS (
        SELECT
          id,
          quantity,
          SUM(quantity) OVER (ORDER BY created_at ASC, id ASC) AS running_total
        FROM usage_events
        WHERE user_id = $1
          AND reported_to_stripe = FALSE
      ),
      selected AS (
        SELECT id
        FROM ordered
        WHERE running_total <= $2
      )
      UPDATE usage_events
      SET reported_to_stripe = TRUE,
          reported_at = NOW()
      WHERE id IN (SELECT id FROM selected)
      `,
      userId,
      amount,
    );
  });
}

export async function getUsersWithPendingUsage(): Promise<PendingUsageRow[]> {
  await ensureUsageTables();

  return prisma.$queryRawUnsafe<PendingUsageRow[]>(`
    SELECT
      uu.user_id AS "userId",
      uu.unreported_usage AS "pendingUsage",
      u."stripeCustomerId" AS "stripeCustomerId",
      u."stripeSubscriptionId" AS "stripeSubscriptionId"
    FROM user_usage uu
    JOIN "User" u
      ON u.id = uu.user_id
    WHERE uu.unreported_usage > 0
      AND u.plan = 'ENTERPRISE'
      AND u."stripeSubscriptionId" IS NOT NULL
  `);
}

export async function getCurrentMonthUsage(userId: string): Promise<number> {
  if (!userId) return 0;
  await ensureUsageTables();

  const [row] = await prisma.$queryRawUnsafe<MonthlyUsageRow[]>(
    `
    SELECT COALESCE(SUM(quantity), 0) AS usage
    FROM usage_events
    WHERE user_id = $1
      AND created_at >= date_trunc('month', NOW())
      AND created_at < (date_trunc('month', NOW()) + INTERVAL '1 month')
    `,
    userId,
  );

  return toNumber(row?.usage ?? 0);
}

export async function getStaleUnreportedEventCount(hours: number = 2): Promise<number> {
  await ensureUsageTables();

  const [row] = await prisma.$queryRawUnsafe<CountRow[]>(
    `
    SELECT COUNT(*) AS count
    FROM usage_events
    WHERE reported_to_stripe = FALSE
      AND created_at < (NOW() - ($1::int * INTERVAL '1 hour'))
    `,
    hours,
  );

  return toNumber(row?.count ?? 0);
}
