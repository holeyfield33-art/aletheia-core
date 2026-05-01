import Link from "next/link";

const protectedAgentCards = [
  {
    title: "Protected Support Agent",
    body: "For customer support bots, internal copilots, and helpdesk workflows. Blocks prompt injection, unsafe refunds, and data exposure before execution.",
    price: "From $500",
    ctaLabel: "Get This Agent",
    href: "mailto:info@aletheia-core.com?subject=Protected Support Agent",
  },
  {
    title: "Protected Outreach Agent",
    body: "For sales follow-up, lead qualification, and client operations. Generates messages but keeps every send human-approved.",
    price: "From $300",
    ctaLabel: "Get This Agent",
    href: "mailto:info@aletheia-core.com?subject=Protected Outreach Agent",
  },
  {
    title: "Protected Trading Signal Agent",
    body: "For signal generation, paper trading, and decision journaling. Signal first, execute later. Every decision signed and auditable.",
    price: "From $300",
    ctaLabel: "View Live Demo",
    href: "https://trader.aletheia-core.com",
  },
] as const;

const exploreCards = [
  {
    title: "AI Agent Security",
    href: "/ai-agent-security",
    description: "Runtime protection for tool-using AI agents.",
  },
  {
    title: "Prompt Injection Protection",
    href: "/prompt-injection-protection",
    description:
      "Block override attempts, unsafe instructions, and data exfiltration prompts.",
  },
  {
    title: "AI Runtime Security",
    href: "/ai-runtime-security",
    description: "Enforce policy before agent actions execute.",
  },
  {
    title: "Signed Audit Receipts",
    href: "/signed-audit-receipts",
    description: "Generate verifiable proof of agent decisions.",
  },
  {
    title: "AI Agent Guardrails",
    href: "/ai-agent-guardrails",
    description: "Add pre-execution safety controls to autonomous systems.",
  },
] as const;

export default function HomepageExtensions() {
  return (
    <>
      <section id="protected-agent-templates" style={{ padding: "4rem 2rem" }}>
        <div className="container">
          <h2
            style={{
              fontFamily: "var(--font-head)",
              fontSize: "1.75rem",
              fontWeight: 800,
              color: "var(--white)",
              marginBottom: "0.5rem",
            }}
          >
            Protected Agent Templates
          </h2>
          <p
            style={{
              color: "var(--silver)",
              marginBottom: "1.5rem",
              fontSize: "1rem",
              lineHeight: 1.65,
            }}
          >
            Deploy AI agents that cannot act recklessly. Premade protected
            agents with human approval, signed decisions, and audit trails.
          </p>

          <div
            className="protected-agent-grid"
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
              gap: "1.25rem",
            }}
          >
            {protectedAgentCards.map((card) => (
              <article
                key={card.title}
                style={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: "10px",
                  padding: "1.35rem",
                  display: "flex",
                  flexDirection: "column",
                  gap: "0.85rem",
                }}
              >
                <h3
                  style={{
                    fontFamily: "var(--font-head)",
                    color: "var(--white)",
                    fontSize: "1.1rem",
                  }}
                >
                  {card.title}
                </h3>
                <p
                  style={{
                    color: "var(--silver)",
                    fontSize: "0.95rem",
                    lineHeight: 1.6,
                    flex: 1,
                  }}
                >
                  {card.body}
                </p>
                <p
                  style={{
                    color: "var(--white)",
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.9rem",
                  }}
                >
                  {card.price}
                </p>
                {card.href.startsWith("/") ? (
                  <Link className="btn-secondary" href={card.href}>
                    {card.ctaLabel}
                  </Link>
                ) : (
                  <a
                    className="btn-secondary"
                    href={card.href}
                    target={card.href.startsWith("http") ? "_blank" : undefined}
                    rel={card.href.startsWith("http") ? "noopener noreferrer" : undefined}
                  >
                    {card.ctaLabel}
                  </a>
                )}
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="explore-aletheia" style={{ padding: "0 2rem 4rem" }}>
        <div className="container">
          <h2
            style={{
              fontFamily: "var(--font-head)",
              fontSize: "1.75rem",
              fontWeight: 800,
              color: "var(--white)",
              marginBottom: "0.5rem",
            }}
          >
            Explore Aletheia Core
          </h2>

          <div
            className="homepage-solutions-grid"
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
              gap: "1rem",
            }}
          >
            {exploreCards.map((card) => (
              <Link
                key={card.href}
                href={card.href}
                style={{
                  border: "1px solid var(--border-hi)",
                  borderRadius: "10px",
                  background: "var(--surface-2)",
                  padding: "1rem",
                  textDecoration: "none",
                }}
              >
                <h3
                  style={{
                    fontFamily: "var(--font-head)",
                    color: "var(--white)",
                    fontSize: "1.05rem",
                    marginBottom: "0.35rem",
                  }}
                >
                  {card.title}
                </h3>
                <p style={{ color: "var(--silver)", fontSize: "0.95rem", lineHeight: 1.6 }}>
                  {card.description}
                </p>
              </Link>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
