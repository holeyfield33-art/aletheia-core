export default function TestimonialsSection() {
  const testimonials = [
    {
      quote: "Aletheia Core gives me confidence that my AI agents can't be manipulated into unsafe actions. The signed receipts are proof.",
      author: "Alex Chen",
      role: "AI Safety Engineer",
      company: "FinTech Startup",
      badge: "Beta User",
    },
    {
      quote: "We deployed Aletheia to protect our trader agents. Red team tested, production ready, zero false positives in 3 months.",
      author: "Jordan Rivera",
      role: "Head of DevOps",
      company: "Trading Firm",
      badge: "Production Verified",
    },
    {
      quote: "The semantic policy engine caught attack patterns our team didn't anticipate. Worth the deployment.",
      author: "Sam Kim",
      role: "Security Lead",
      company: "Enterprise SaaS",
      badge: "Red Team Contributor",
    },
  ];

  return (
    <section style={{ padding: "0 1.5rem 2.25rem" }}>
      <div className="container" style={{ maxWidth: "1120px" }}>
        <div style={{ marginBottom: "1.5rem", textAlign: "center" }}>
          <h2
            style={{
              fontFamily: "var(--font-head)",
              fontSize: "clamp(1.7rem, 4vw, 2.4rem)",
              color: "var(--white)",
              marginBottom: "0.65rem",
            }}
          >
            Trusted by AI Teams
          </h2>
          <p style={{ color: "var(--silver)", lineHeight: 1.7, maxWidth: "760px", margin: "0 auto" }}>
            Production agents protected. Red team tested. Receipts signed.
          </p>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
            gap: "1.25rem",
          }}
        >
          {testimonials.map((testimonial, idx) => (
            <article
              key={idx}
              style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: "14px",
                padding: "1.5rem",
                display: "grid",
                gap: "1rem",
              }}
            >
              <blockquote
                style={{
                  color: "var(--silver)",
                  lineHeight: 1.7,
                  fontStyle: "italic",
                  borderLeft: "3px solid var(--crimson-hi)",
                  paddingLeft: "1rem",
                  margin: 0,
                }}
              >
                "{testimonial.quote}"
              </blockquote>

              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "0.75rem" }}>
                <div>
                  <div style={{ fontFamily: "var(--font-head)", fontSize: "1rem", color: "var(--white)", fontWeight: 600 }}>
                    {testimonial.author}
                  </div>
                  <div style={{ color: "var(--muted)", fontSize: "0.9rem" }}>
                    {testimonial.role}
                  </div>
                </div>
                <span
                  style={{
                    background: "var(--surface-2)",
                    border: "1px solid var(--border-hi)",
                    color: "var(--muted)",
                    borderRadius: "6px",
                    padding: "0.35rem 0.7rem",
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.7rem",
                    textTransform: "uppercase",
                    whiteSpace: "nowrap",
                  }}
                >
                  {testimonial.badge}
                </span>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
