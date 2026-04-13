"use client";

import { useState, useEffect, useCallback } from "react";

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

export default function LogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [filterDecision, setFilterDecision] = useState("");
  const pageSize = 25;

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: String(page),
        limit: String(pageSize),
      });
      if (filterDecision) params.set("decision", filterDecision);
      const res = await fetch(`/api/logs?${params}`);
      if (res.ok) {
        const data = await res.json();
        setLogs(data.logs || []);
        setTotal(data.total || 0);
      }
    } catch {
      /* non-critical */
    } finally {
      setLoading(false);
    }
  }, [page, filterDecision]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const decisionColor = (d: string) => {
    if (d === "PROCEED") return "var(--green)";
    if (d === "DENIED" || d === "SANDBOX_BLOCKED") return "var(--crimson-hi)";
    return "var(--muted)";
  };

  return (
    <div>
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
          onChange={(e) => { setFilterDecision(e.target.value); setPage(1); }}
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
        <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", color: "var(--muted)" }}>
          {total.toLocaleString()} total records
        </span>
      </div>

      {/* Table */}
      <div style={{ border: "1px solid var(--border)", overflow: "auto", marginBottom: "1rem" }}>
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontFamily: "var(--font-mono)",
            fontSize: "0.75rem",
          }}
        >
          <thead>
            <tr style={{ borderBottom: "1px solid var(--border)" }}>
              {["Time", "Decision", "Action", "Origin", "Score", "Reason", "Request ID"].map((h) => (
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
                <tr key={`skel-${i}`} style={{ borderBottom: "1px solid var(--border)" }}>
                  {[80, 50, 65, 55, 30, 70, 40].map((w, j) => (
                    <td key={j} style={{ padding: "0.55rem 0.65rem" }}>
                      <div className="skeleton-text" style={{ width: `${w}%` }} />
                    </td>
                  ))}
                </tr>
              ))
            ) : logs.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ padding: "2rem", textAlign: "center", color: "var(--muted)" }}>
                  No audit logs found. Make API requests to generate decision receipts.
                </td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id} style={{ borderBottom: "1px solid var(--border)" }}>
                  <td style={{ padding: "0.45rem 0.65rem", color: "var(--muted)", whiteSpace: "nowrap" }}>
                    {new Date(log.createdAt).toLocaleString()}
                  </td>
                  <td style={{ padding: "0.45rem 0.65rem" }}>
                    <span
                      style={{
                        padding: "0.12rem 0.45rem",
                        fontSize: "0.65rem",
                        fontWeight: 600,
                        letterSpacing: "0.04em",
                        background: log.decision === "PROCEED" ? "rgba(46,184,122,0.12)" : "rgba(176,34,54,0.15)",
                        color: decisionColor(log.decision),
                        textTransform: "uppercase",
                      }}
                    >
                      {log.decision}
                    </span>
                  </td>
                  <td style={{ padding: "0.45rem 0.65rem", color: "var(--white)" }}>
                    {log.action}
                  </td>
                  <td style={{ padding: "0.45rem 0.65rem", color: "var(--silver)" }}>
                    {log.origin || "—"}
                  </td>
                  <td style={{ padding: "0.45rem 0.65rem", color: "var(--silver)" }}>
                    {log.threatScore != null ? log.threatScore.toFixed(2) : "—"}
                  </td>
                  <td style={{ padding: "0.45rem 0.65rem", color: "var(--muted)", fontSize: "0.68rem" }}>
                    {log.reason || "—"}
                  </td>
                  <td
                    style={{
                      padding: "0.45rem 0.65rem",
                      color: "var(--muted)",
                      fontSize: "0.65rem",
                      maxWidth: "120px",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                    title={log.requestId || ""}
                  >
                    {log.requestId ? log.requestId.slice(0, 16) + "…" : "—"}
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
          <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", color: "var(--muted)" }}>
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
    </div>
  );
}
