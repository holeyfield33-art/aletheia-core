"use client";

import { useState, useEffect, useCallback } from "react";
import { clientFetch } from "@/lib/client-fetch";

interface AuditLog {
  id: string;
  decision: string;
  action: string;
  origin: string | null;
  threatScore: number | null;
  reason: string | null;
  requestId: string | null;
  createdAt: string;
}

interface AuditLogsResponse {
  logs?: AuditLog[];
  total?: number;
}

interface AuditLogDetail extends AuditLog {
  latencyMs: number | null;
  receipt: Record<string, unknown> | null;
}

interface AuditLogDetailResponse {
  log?: AuditLogDetail;
}

const screenReaderOnly: React.CSSProperties = {
  position: "absolute",
  width: "1px",
  height: "1px",
  padding: 0,
  margin: "-1px",
  overflow: "hidden",
  clip: "rect(0, 0, 0, 0)",
  whiteSpace: "nowrap",
  border: 0,
};

export default function LogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [copiedRequestId, setCopiedRequestId] = useState<string | null>(null);
  const [copiedReceipt, setCopiedReceipt] = useState(false);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [filterDecision, setFilterDecision] = useState("");
  const [selectedLog, setSelectedLog] = useState<AuditLogDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const pageSize = 25;

  const handleCopyRequestId = useCallback(async (requestId: string) => {
    try {
      await navigator.clipboard.writeText(requestId);
      setCopiedRequestId(requestId);
      window.setTimeout(() => {
        setCopiedRequestId((current) => (current === requestId ? null : current));
      }, 1500);
    } catch {
      // No-op: clipboard may be blocked by browser permissions.
    }
  }, []);

  const loadDetail = useCallback(async (id: string) => {
    setDetailLoading(true);
    try {
      const data = await clientFetch<AuditLogDetailResponse>(`/api/logs/${id}`);
      setSelectedLog(data.log ?? null);
    } catch {
      // best-effort
    } finally {
      setDetailLoading(false);
    }
  }, []);

  const handleCopyReceipt = useCallback(
    async (receipt: Record<string, unknown>) => {
      try {
        await navigator.clipboard.writeText(JSON.stringify(receipt, null, 2));
        setCopiedReceipt(true);
        window.setTimeout(() => setCopiedReceipt(false), 1500);
      } catch {
        // No-op
      }
    },
    [],
  );

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    setFetchError(null);
    try {
      const params = new URLSearchParams({
        page: String(page),
        limit: String(pageSize),
      });
      if (filterDecision) params.set("decision", filterDecision);
      const data = await clientFetch<AuditLogsResponse>(`/api/logs?${params}`);
      setLogs(data.logs || []);
      setTotal(data.total || 0);
    } catch {
      setFetchError("Unable to reach the server.");
    } finally {
      setLoading(false);
    }
  }, [page, filterDecision]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const liveMessage = loading
    ? "Loading audit log table"
    : fetchError
      ? fetchError
      : logs.length === 0
        ? "No audit logs found."
        : `Showing ${logs.length} audit logs on page ${page} of ${totalPages}. ${total.toLocaleString()} total records.`;

  const decisionColor = (d: string) => {
    if (d === "PROCEED") return "var(--green)";
    if (d === "DENIED" || d === "SANDBOX_BLOCKED") return "var(--crimson-hi)";
    return "var(--muted)";
  };

  return (
    <div>
      <div aria-live="polite" role="status" style={screenReaderOnly}>
        {liveMessage}
      </div>
      <div
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "0.7rem",
          color: "var(--muted)",
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          marginBottom: "0.75rem",
        }}
      >
        Audit Logs
      </div>
      <h1
        style={{
          fontFamily: "var(--font-head)",
          fontSize: "1.5rem",
          fontWeight: 800,
          color: "var(--white)",
          marginBottom: "1.25rem",
        }}
      >
        Decision Receipts
      </h1>

      {/* Filters */}
      <div
        style={{
          display: "flex",
          gap: "0.75rem",
          marginBottom: "1.25rem",
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        <select
          value={filterDecision}
          onChange={(e) => {
            setFilterDecision(e.target.value);
            setPage(1);
          }}
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            color: "var(--silver)",
            padding: "0.4rem 0.65rem",
            fontFamily: "var(--font-mono)",
            fontSize: "0.78rem",
          }}
        >
          <option value="">All decisions</option>
          <option value="PROCEED">PROCEED</option>
          <option value="DENIED">DENIED</option>
          <option value="SANDBOX_BLOCKED">SANDBOX_BLOCKED</option>
        </select>
        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "0.72rem",
            color: "var(--muted)",
          }}
        >
          {total.toLocaleString()} total records
        </span>
      </div>

      {/* Table */}
      {fetchError && (
        <div
          style={{
            color: "var(--crimson-hi)",
            marginBottom: "1rem",
            fontSize: "0.85rem",
          }}
        >
          {fetchError}
        </div>
      )}
      <div
        style={{
          border: "1px solid var(--border)",
          overflow: "auto",
          marginBottom: "1rem",
        }}
      >
        <table
          aria-describedby="audit-logs-live-region"
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontFamily: "var(--font-mono)",
            fontSize: "0.75rem",
          }}
        >
          <caption id="audit-logs-live-region" style={screenReaderOnly}>
            Audit log table with time, decision, action, origin, threat score,
            reason, and request ID columns.
          </caption>
          <thead>
            <tr style={{ borderBottom: "1px solid var(--border)" }}>
              {[
                "Time",
                "Decision",
                "Action",
                "Origin",
                "Score",
                "Reason",
                "Request ID",
              ].map((h) => (
                <th
                  key={h}
                  style={{
                    textAlign: "left",
                    padding: "0.55rem 0.65rem",
                    color: "var(--muted)",
                    fontWeight: 500,
                    fontSize: "0.68rem",
                    letterSpacing: "0.06em",
                    textTransform: "uppercase",
                    whiteSpace: "nowrap",
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 6 }).map((_, i) => (
                <tr
                  key={`skel-${i}`}
                  style={{ borderBottom: "1px solid var(--border)" }}
                >
                  {[80, 50, 65, 55, 30, 70, 40].map((w, j) => (
                    <td key={j} style={{ padding: "0.55rem 0.65rem" }}>
                      <div
                        className="skeleton-text"
                        style={{ width: `${w}%` }}
                      />
                    </td>
                  ))}
                </tr>
              ))
            ) : logs.length === 0 ? (
              <tr>
                <td
                  colSpan={7}
                  style={{
                    padding: "2rem",
                    textAlign: "center",
                    color: "var(--muted)",
                  }}
                >
                  No audit logs found. Make API requests to generate decision
                  receipts.
                </td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr
                  key={log.id}
                  onClick={() => void loadDetail(log.id)}
                  style={{
                    borderBottom: "1px solid var(--border)",
                    cursor: "pointer",
                  }}
                >
                  <td
                    style={{
                      padding: "0.45rem 0.65rem",
                      color: "var(--muted)",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {new Date(log.createdAt).toLocaleString()}
                  </td>
                  <td style={{ padding: "0.45rem 0.65rem" }}>
                    <span
                      style={{
                        padding: "0.12rem 0.45rem",
                        fontSize: "0.65rem",
                        fontWeight: 600,
                        letterSpacing: "0.04em",
                        background:
                          log.decision === "PROCEED"
                            ? "rgba(46,184,122,0.12)"
                            : "rgba(176,34,54,0.15)",
                        color: decisionColor(log.decision),
                        textTransform: "uppercase",
                      }}
                    >
                      {log.decision}
                    </span>
                  </td>
                  <td
                    style={{
                      padding: "0.45rem 0.65rem",
                      color: "var(--white)",
                    }}
                  >
                    {log.action}
                  </td>
                  <td
                    style={{
                      padding: "0.45rem 0.65rem",
                      color: "var(--silver)",
                    }}
                  >
                    {log.origin || "—"}
                  </td>
                  <td
                    style={{
                      padding: "0.45rem 0.65rem",
                      color: "var(--silver)",
                    }}
                  >
                    {log.threatScore != null ? log.threatScore.toFixed(2) : "—"}
                  </td>
                  <td
                    style={{
                      padding: "0.45rem 0.65rem",
                      color: "var(--muted)",
                      fontSize: "0.68rem",
                    }}
                  >
                    {log.reason || "—"}
                  </td>
                  <td
                    style={{
                      padding: "0.45rem 0.65rem",
                      color: "var(--muted)",
                      fontSize: "0.65rem",
                      maxWidth: "200px",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "normal",
                    }}
                    title={log.requestId || ""}
                  >
                    {log.requestId ? (
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "0.35rem",
                          flexWrap: "wrap",
                        }}
                      >
                        <span
                          style={{
                            fontFamily: "var(--font-mono)",
                            color: "var(--silver)",
                          }}
                        >
                          {log.requestId}
                        </span>
                        <button
                          type="button"
                          onClick={() => {
                            if (log.requestId) {
                              void handleCopyRequestId(log.requestId);
                            }
                          }}
                          style={{
                            border: "1px solid var(--border)",
                            background: "var(--surface)",
                            color: "var(--muted)",
                            fontFamily: "var(--font-mono)",
                            fontSize: "0.62rem",
                            padding: "0.12rem 0.35rem",
                            cursor: "pointer",
                          }}
                          aria-label={`Copy request ID ${log.requestId}`}
                        >
                          {copiedRequestId === log.requestId ? "Copied" : "Copy"}
                        </button>
                      </div>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              color: page <= 1 ? "var(--muted)" : "var(--silver)",
              padding: "0.35rem 0.75rem",
              fontFamily: "var(--font-mono)",
              fontSize: "0.75rem",
              cursor: page <= 1 ? "default" : "pointer",
            }}
          >
            Prev
          </button>
          <span
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "0.72rem",
              color: "var(--muted)",
            }}
          >
            {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              color: page >= totalPages ? "var(--muted)" : "var(--silver)",
              padding: "0.35rem 0.75rem",
              fontFamily: "var(--font-mono)",
              fontSize: "0.75rem",
              cursor: page >= totalPages ? "default" : "pointer",
            }}
          >
            Next
          </button>
        </div>
      )}

      {/* Detail panel */}
      {selectedLog && (
        <>
          {/* Backdrop (mobile) */}
          <div
            onClick={() => setSelectedLog(null)}
            style={{
              position: "fixed",
              inset: 0,
              background: "rgba(0,0,0,0.55)",
              zIndex: 40,
              display: "none",
            }}
            className="log-detail-backdrop"
          />
          {/* Panel */}
          <div
            className="log-detail-panel"
            style={{
              position: "fixed",
              top: 0,
              right: 0,
              bottom: 0,
              width: "420px",
              background: "var(--surface, #111)",
              borderLeft: "1px solid var(--border)",
              zIndex: 50,
              overflowY: "auto",
              padding: "1.5rem",
              display: "flex",
              flexDirection: "column",
              gap: "1rem",
            }}
          >
            {/* Header */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.7rem",
                  color: "var(--muted)",
                  textTransform: "uppercase",
                  letterSpacing: "0.1em",
                }}
              >
                Receipt Detail
              </span>
              <button
                type="button"
                onClick={() => setSelectedLog(null)}
                style={{
                  background: "none",
                  border: "1px solid var(--border)",
                  color: "var(--silver)",
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.75rem",
                  padding: "0.2rem 0.6rem",
                  cursor: "pointer",
                }}
                aria-label="Close detail panel"
              >
                Close
              </button>
            </div>

            {/* Decision badge */}
            <div>
              <span
                style={{
                  padding: "0.2rem 0.55rem",
                  fontSize: "0.7rem",
                  fontWeight: 700,
                  letterSpacing: "0.06em",
                  textTransform: "uppercase",
                  background:
                    selectedLog.decision === "PROCEED"
                      ? "rgba(46,184,122,0.15)"
                      : "rgba(176,34,54,0.18)",
                  color:
                    selectedLog.decision === "PROCEED"
                      ? "var(--green)"
                      : "var(--crimson-hi)",
                }}
              >
                {selectedLog.decision}
              </span>
            </div>

            {/* Meta fields */}
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontFamily: "var(--font-mono)",
                fontSize: "0.75rem",
              }}
            >
              <tbody>
                {(
                  [
                    ["Time", new Date(selectedLog.createdAt).toLocaleString()],
                    ["Action", selectedLog.action],
                    ["Origin", selectedLog.origin ?? "—"],
                    ["Threat Score", selectedLog.threatScore != null ? selectedLog.threatScore.toFixed(2) : "—"],
                    ["Latency", selectedLog.latencyMs != null ? `${selectedLog.latencyMs.toFixed(0)} ms` : "—"],
                    ["Reason", selectedLog.reason ?? "—"],
                  ] as [string, string][]
                ).map(([label, value]) => (
                  <tr key={label} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "0.4rem 0.35rem 0.4rem 0", color: "var(--muted)", width: "120px" }}>
                      {label}
                    </td>
                    <td style={{ padding: "0.4rem 0", color: "var(--silver)", wordBreak: "break-word" }}>
                      {value}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Request ID row */}
            {selectedLog.requestId && (
              <div>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem", color: "var(--muted)", marginBottom: "0.35rem" }}>
                  Request ID
                </div>
                <div style={{ display: "flex", gap: "0.5rem", alignItems: "flex-start", flexWrap: "wrap" }}>
                  <code style={{ fontSize: "0.68rem", color: "var(--silver)", wordBreak: "break-all" }}>
                    {selectedLog.requestId}
                  </code>
                  <button
                    type="button"
                    onClick={() => void handleCopyRequestId(selectedLog.requestId!)}
                    style={{
                      border: "1px solid var(--border)",
                      background: "var(--surface)",
                      color: "var(--muted)",
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.62rem",
                      padding: "0.12rem 0.35rem",
                      cursor: "pointer",
                      flexShrink: 0,
                    }}
                  >
                    {copiedRequestId === selectedLog.requestId ? "Copied" : "Copy"}
                  </button>
                </div>
              </div>
            )}

            {/* Receipt JSON */}
            <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "0.35rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem", color: "var(--muted)" }}>
                  Receipt JSON
                </span>
                {selectedLog.receipt && (
                  <button
                    type="button"
                    onClick={() => void handleCopyReceipt(selectedLog.receipt!)}
                    style={{
                      border: "1px solid var(--border)",
                      background: "var(--surface)",
                      color: "var(--muted)",
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.62rem",
                      padding: "0.12rem 0.4rem",
                      cursor: "pointer",
                    }}
                  >
                    {copiedReceipt ? "Copied" : "Copy all"}
                  </button>
                )}
              </div>
              <pre
                style={{
                  background: "#0a0a0b",
                  border: "1px solid var(--border)",
                  padding: "0.75rem",
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.67rem",
                  color: "var(--silver)",
                  overflowX: "auto",
                  overflowY: "auto",
                  maxHeight: "320px",
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-all",
                  flex: 1,
                }}
              >
                {selectedLog.receipt
                  ? JSON.stringify(selectedLog.receipt, null, 2)
                  : "No receipt available for this decision."}
              </pre>
            </div>

            {/* Verify signature button (disabled — wired in follow-up) */}
            <button
              type="button"
              disabled
              title="Signature verification coming soon"
              style={{
                border: "1px solid var(--border)",
                background: "transparent",
                color: "var(--muted)",
                fontFamily: "var(--font-mono)",
                fontSize: "0.75rem",
                padding: "0.5rem 1rem",
                cursor: "not-allowed",
                opacity: 0.5,
              }}
            >
              Verify Signature
            </button>
          </div>
        </>
      )}
      {detailLoading && (
        <div
          style={{
            position: "fixed",
            bottom: "1.5rem",
            right: "1.5rem",
            background: "var(--surface)",
            border: "1px solid var(--border)",
            padding: "0.5rem 1rem",
            fontFamily: "var(--font-mono)",
            fontSize: "0.72rem",
            color: "var(--muted)",
            zIndex: 60,
          }}
        >
          Loading...
        </div>
      )}
    </div>
  );
}
