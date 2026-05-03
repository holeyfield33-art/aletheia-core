import { SEO_SOLUTIONS } from "@/lib/site-config";

type FaqEntry = {
  q: string;
  a: string;
};

type SeoLandingProps = {
  slug: string;
  eyebrow: string;
  title: string;
  subtitle: string;
  problemPoints: string[];
  flowSteps: Array<{ name: string; detail: string }>;
  useCases: string[];
  faq: FaqEntry[];
  primaryCta: { label: string; href: string };
  secondaryCta: { label: string; href: string };
};

export default function SeoLanding({
  slug,
  eyebrow,
  title,
  subtitle,
  problemPoints,
  flowSteps,
  useCases,
  faq,
  primaryCta,
  secondaryCta,
}: SeoLandingProps) {
  const faqJsonLd = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faq.map((entry) => ({
      "@type": "Question",
      name: entry.q,
      acceptedAnswer: {
        "@type": "Answer",
        text: entry.a,
      },
    })),
  };

  const related = SEO_SOLUTIONS.filter((entry) => entry.href !== slug);

  return (
    <section className="seo-landing-shell" style={{ padding: "4rem 2rem 5rem" }}>
      <div className="container" style={{ maxWidth: "980px" }}>
        <div
          style={{
            display: "inline-block",
            fontFamily: "var(--font-mono)",
            fontSize: "0.7rem",
            color: "var(--silver)",
            background: "var(--crimson-glow)",
            border: "1px solid var(--crimson)",
            borderRadius: "999px",
            padding: "0.25rem 0.7rem",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            marginBottom: "1rem",
          }}
        >
          {eyebrow}
        </div>
        <h1
          style={{
            fontFamily: "var(--font-head)",
            fontWeight: 800,
            fontSize: "clamp(1.8rem, 4.5vw, 2.8rem)",
            color: "var(--white)",
            lineHeight: 1.18,
            marginBottom: "1rem",
          }}
        >
          {title}
        </h1>
        <p
          style={{
            color: "var(--silver)",
            fontSize: "1rem",
            lineHeight: 1.7,
            maxWidth: "720px",
            marginBottom: "1.5rem",
          }}
        >
          {subtitle}
        </p>

        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem", marginBottom: "3rem" }}>
          <a className="btn-primary" href={primaryCta.href}>
            {primaryCta.label}
          </a>
          <a className="btn-secondary" href={secondaryCta.href}>
            {secondaryCta.label}
          </a>
        </div>

        <div className="seo-landing-grid" style={{ display: "grid", gridTemplateColumns: "1.05fr 0.95fr", gap: "1.25rem", marginBottom: "1.25rem" }}>
          <article
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: "10px",
              padding: "1.35rem",
            }}
          >
            <h2
              style={{
                fontFamily: "var(--font-head)",
                fontSize: "1.25rem",
                marginBottom: "0.85rem",
              }}
            >
              Common failure patterns
            </h2>
            <ul style={{ marginLeft: "1.1rem", color: "var(--silver)", lineHeight: 1.75 }}>
              {problemPoints.map((point) => (
                <li key={point}>{point}</li>
              ))}
            </ul>
          </article>

          <article
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: "10px",
              padding: "1.35rem",
            }}
          >
            <h2
              style={{
                fontFamily: "var(--font-head)",
                fontSize: "1.25rem",
                marginBottom: "0.85rem",
              }}
            >
              Operational outcomes
            </h2>
            <ul style={{ marginLeft: "1.1rem", color: "var(--silver)", lineHeight: 1.75 }}>
              {useCases.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>
        </div>

        <article
          style={{
            background: "linear-gradient(180deg, var(--surface), var(--surface-2))",
            border: "1px solid var(--border-hi)",
            borderRadius: "10px",
            padding: "1.35rem",
            marginBottom: "1.25rem",
          }}
        >
          <h2
            style={{
              fontFamily: "var(--font-head)",
              fontSize: "1.2rem",
              marginBottom: "1rem",
            }}
          >
            How the control path works
          </h2>
          <div style={{ display: "grid", gap: "0.8rem" }}>
            {flowSteps.map((step) => (
              <div
                key={step.name}
                style={{
                  background: "rgba(0, 0, 0, 0.16)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px",
                  padding: "0.8rem 0.95rem",
                }}
              >
                <h3
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.78rem",
                    color: "var(--crimson-hi)",
                    letterSpacing: "0.08em",
                    textTransform: "uppercase",
                    marginBottom: "0.35rem",
                  }}
                >
                  {step.name}
                </h3>
                <p style={{ color: "var(--silver)", fontSize: "0.92rem", lineHeight: 1.65 }}>
                  {step.detail}
                </p>
              </div>
            ))}
          </div>
        </article>

        <article
          id="explore-aletheia"
          style={{
            border: "1px solid var(--border)",
            borderRadius: "10px",
            background: "var(--surface)",
            padding: "1.35rem",
            marginBottom: "1.25rem",
          }}
        >
          <h2 style={{ fontFamily: "var(--font-head)", fontSize: "1.2rem", marginBottom: "0.7rem" }}>
            Explore Aletheia Core
          </h2>
          <p style={{ color: "var(--silver)", marginBottom: "1rem" }}>
            Browse adjacent designs used by security teams to stage runtime controls.
          </p>
          <div className="seo-landing-grid" style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "0.8rem" }}>
            {related.map((entry) => (
              <a
                key={entry.href}
                href={entry.href}
                style={{
                  border: "1px solid var(--border-hi)",
                  borderRadius: "8px",
                  background: "var(--surface-2)",
                  padding: "0.8rem",
                  textDecoration: "none",
                }}
              >
                <h3
                  style={{
                    fontFamily: "var(--font-head)",
                    color: "var(--white)",
                    fontSize: "0.98rem",
                    marginBottom: "0.3rem",
                  }}
                >
                  {entry.title}
                </h3>
                <p style={{ color: "var(--muted)", fontSize: "0.84rem", lineHeight: 1.5 }}>
                  {entry.summary}
                </p>
              </a>
            ))}
          </div>
        </article>

        <article
          style={{
            border: "1px solid var(--border)",
            borderRadius: "10px",
            background: "var(--surface)",
            padding: "1.35rem",
          }}
        >
          <h2
            style={{
              fontFamily: "var(--font-head)",
              fontSize: "1.2rem",
              marginBottom: "1rem",
            }}
          >
            FAQ
          </h2>
          <div className="seo-landing-faq" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.8rem" }}>
            {faq.map((entry) => (
              <div key={entry.q} style={{ border: "1px solid var(--border-hi)", borderRadius: "8px", padding: "0.85rem" }}>
                <h3 style={{ color: "var(--white)", fontSize: "0.95rem", marginBottom: "0.35rem" }}>{entry.q}</h3>
                <p style={{ color: "var(--silver)", fontSize: "0.86rem", lineHeight: 1.6 }}>{entry.a}</p>
              </div>
            ))}
          </div>
        </article>
      </div>

      <script
        type="application/ld+json"
      >
        {JSON.stringify(faqJsonLd)}
      </script>
    </section>
  );
}
