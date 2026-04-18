import type { Metadata } from "next";
import { PRODUCT, URLS, STATUS } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "System Status",
  description: `Operational status of ${PRODUCT.name} services.`,
};

interface ServiceEntry {
  name: string;
  description: string;
  status: "operational" | "degraded" | "down";
}

function getServices(): ServiceEntry[] {
  return [
    {
      name: "Hosted API",
      description: "Audit endpoint at api.aletheia-core.com",
      status: (STATUS.hostedApi as string) === "live" ? "operational" : "down",
    },
    {
      name: "Web Dashboard",
      description: "app.aletheia-core.com — account, keys, logs",
      status: "operational",
    },
    {
      name: "Authentication",
      description: "NextAuth.js + Prisma — login, register, OAuth",
      status: "operational",
    },
    {
      name: "Stripe Billing",
      description: "Subscription management and checkout",
      status: "operational",
    },
    {
      name: "Documentation",
      description: "aletheia-core.com — landing and docs",
      status: "operational",
    },
  ];
}

const statusColor: Record<string, string> = {
  operational: "var(--green)",
  degraded: "#e67e22",
  down: "var(--crimson-hi)",
};

const statusLabel: Record<string, string> = {
  operational: "Operational",
  degraded: "Degraded",
  down: "Down",
};

export default function StatusPage() {
  const services = getServices();
  const allOperational = services.every((s) => s.status === "operational");

  return (
    <div
      style={{
        maxWidth: "700px",
        margin: "0 auto",
        padding: "3rem 2rem 4rem",
      }}
    >
      <div
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "0.7rem",
          color: "var(--muted)",
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          marginBottom: "0.5rem",
        }}
      >
        System Status
      </div>
      <h1
        style={{
          fontFamily: "var(--font-head)",
          fontSize: "1.8rem",
          fontWeight: 800,
          color: "var(--white)",
          marginBottom: "1.5rem",
        }}
      >
        {PRODUCT.name} Status
      </h1>

      {/* Overall status banner */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.75rem",
          padding: "1rem 1.25rem",
          background: allOperational ? "rgba(46,184,122,0.08)" : "rgba(230,126,34,0.08)",
          border: `1px solid ${allOperational ? "rgba(46,184,122,0.25)" : "rgba(230,126,34,0.25)"}`,
          borderRadius: "8px",
          marginBottom: "2rem",
        }}
      >
        <div
          style={{
            width: "10px",
            height: "10px",
            borderRadius: "50%",
            background: allOperational ? "var(--green)" : "#e67e22",
            flexShrink: 0,
          }}
        />
        <span
          style={{
            fontFamily: "var(--font-head)",
            fontSize: "1rem",
            fontWeight: 700,
            color: allOperational ? "var(--green)" : "#e67e22",
          }}
        >
          {allOperational ? "All Systems Operational" : "Some Systems Experiencing Issues"}
        </span>
      </div>

      {/* Individual services */}
      <div style={{ display: "flex", flexDirection: "column", gap: "0" }}>
        {services.map((s) => (
          <div
            key={s.name}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "1rem 0",
              borderBottom: "1px solid var(--border)",
            }}
          >
            <div>
              <div
                style={{
                  fontFamily: "var(--font-head)",
                  fontSize: "0.95rem",
                  fontWeight: 600,
                  color: "var(--white)",
                  marginBottom: "0.15rem",
                }}
              >
                {s.name}
              </div>
              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.75rem",
                  color: "var(--muted)",
                }}
              >
                {s.description}
              </div>
            </div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                flexShrink: 0,
              }}
            >
              <div
                style={{
                  width: "8px",
                  height: "8px",
                  borderRadius: "50%",
                  background: statusColor[s.status],
                }}
              />
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.78rem",
                  color: statusColor[s.status],
                }}
              >
                {statusLabel[s.status]}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Footer info */}
      <div
        style={{
          marginTop: "2.5rem",
          padding: "1.25rem",
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "8px",
        }}
      >
        <p
          style={{
            fontSize: "0.82rem",
            color: "var(--silver)",
            lineHeight: 1.65,
            marginBottom: "0.75rem",
          }}
        >
          This page reflects the current configuration status of {PRODUCT.name} services.
          For real-time incident updates and historical uptime data, check back here or
          follow our GitHub repository.
        </p>
        <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
          <a
            href={URLS.github}
            style={{ color: "var(--crimson-hi)", fontSize: "0.82rem", textDecoration: "none" }}
          >
            GitHub &rarr;
          </a>
          <a
            href={`mailto:${URLS.contactEmail}?subject=Status Inquiry`}
            style={{ color: "var(--crimson-hi)", fontSize: "0.82rem", textDecoration: "none" }}
          >
            Report an Issue &rarr;
          </a>
        </div>
      </div>

      <p
        style={{
          marginTop: "1.5rem",
          fontSize: "0.75rem",
          color: "var(--muted)",
          fontFamily: "var(--font-mono)",
          textAlign: "center",
        }}
      >
        v{PRODUCT.version} · Last checked: {new Date().toISOString().slice(0, 16).replace("T", " ")} UTC
      </p>
    </div>
  );
}
