export interface HostedApiKey {
  id: string;
  name: string;
  keyPrefix: string;
  plan: string;
  status: string;
  monthlyQuota: number;
  requestsUsed: number;
  periodStart: string;
  periodEnd: string;
  createdAt: string;
  lastUsedAt: string | null;
}

export interface HostedApiKeyRecord {
  id: string;
  name: string;
  key_prefix: string;
  plan: string;
  status: string;
  monthly_quota: number;
  requests_used: number;
  period_start: string;
  period_end: string;
  created_at: string;
  last_used_at: string | null;
}

export interface CreateHostedApiKeyRecord extends HostedApiKeyRecord {
  key: string;
}

export interface RawHostedApiKey extends Partial<HostedApiKey> {
  key_prefix?: string;
  monthly_quota?: number;
  requests_used?: number;
  period_start?: string;
  period_end?: string;
  created_at?: string;
  last_used_at?: string | null;
}

export function normalizeHostedApiKey(key: RawHostedApiKey): HostedApiKey {
  return {
    id: String(key.id ?? ""),
    name: String(key.name ?? ""),
    keyPrefix: String(key.keyPrefix ?? key.key_prefix ?? ""),
    plan: String(key.plan ?? ""),
    status: String(key.status ?? ""),
    monthlyQuota: Number(key.monthlyQuota ?? key.monthly_quota ?? 0),
    requestsUsed: Number(key.requestsUsed ?? key.requests_used ?? 0),
    periodStart: String(key.periodStart ?? key.period_start ?? ""),
    periodEnd: String(key.periodEnd ?? key.period_end ?? ""),
    createdAt: String(key.createdAt ?? key.created_at ?? ""),
    lastUsedAt: key.lastUsedAt ?? key.last_used_at ?? null,
  };
}

export function serializeHostedApiKey(key: {
  id: string;
  name: string;
  keyPrefix: string;
  plan: string;
  status: string;
  monthlyQuota: number;
  requestsUsed: number;
  periodStart: Date;
  periodEnd: Date;
  createdAt: Date;
  lastUsedAt: Date | null;
}): HostedApiKeyRecord {
  return {
    id: key.id,
    name: key.name,
    key_prefix: key.keyPrefix,
    plan: key.plan,
    status: key.status,
    monthly_quota: key.monthlyQuota,
    requests_used: key.requestsUsed,
    period_start: key.periodStart.toISOString(),
    period_end: key.periodEnd.toISOString(),
    created_at: key.createdAt.toISOString(),
    last_used_at: key.lastUsedAt ? key.lastUsedAt.toISOString() : null,
  };
}
