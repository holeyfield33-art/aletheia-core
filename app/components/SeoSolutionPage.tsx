import Link from "next/link";
import { SEO_SOLUTIONS } from "@/lib/site-config";

type FaqItem = {
  q: string;
  a: string;
};

type SeoSolutionPageProps = {
  slug: string;
  title: string;
  hero: string;
  problemPoints: string[];
  solveHeading: string;
  solveSteps: string[];
  useCases: string[];
  faq: FaqItem[];
  faqSchema: {
    "@context": string;
    "@type": string;
    mainEntity: Array<{
      "@type": string;
      name: string;
      acceptedAnswer: {
        "@type": string;
        text: string;
      };
    }>;
  };
};

export default function SeoSolutionPage({
  slug,
  title,
  hero,
  problemPoints,
  solveHeading,
  solveSteps,
  useCases,
  faq,
  faqSchema,
}: SeoSolutionPageProps) {
  return (
    <section className="seo-landing-shell" style={{ padding: "4rem 2rem 5rem" }}>
      <div className="container" style={{ maxWidth: "980px" }}>
        <h1
          className="seo-page-h1"
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
            maxWidth: "760px",
            marginBottom: "1.5rem",
          }}
        >
          {hero}
        </p>

        <article
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "10px",
            padding: "1.35rem",
            marginBottom: "1rem",
          }}
        >
          <h2
            style={{
              fontFamily: "var(--font-head)",
              fontSize: "1.2rem",
              marginBottom: "0.8rem",
            }}
          >
            Problem
          </h2>
          <ul style={{ marginLeft: "1.1rem", color: "var(--silver)", lineHeight: 1.75 }}>
            {problemPoints.map((point) => (
              <li key={point}>{point}</li>
            ))}
          </ul>
        </article>

        <article
          style={{
            background: "linear-gradient(180deg, var(--surface), var(--surface-2))",
            border: "1px solid var(--border-hi)",
            borderRadius: "10px",
            padding: "1.35rem",
            marginBottom: "1rem",
          }}
        >
          <h2
            style={{
              fontFamily: "var(--font-head)",
              fontSize: "1.2rem",
              marginBottom: "0.8rem",
            }}
          >
            {solveHeading}
          </h2>
          <ol style={{ marginLeft: "1.1rem", color: "var(--silver)", lineHeight: 1.75 }}>
            {solveSteps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </article>

        <article
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "10px",
            padding: "1.35rem",
            marginBottom: "1rem",
          }}
        >
          <h2
            style={{
              fontFamily: "var(--font-head)",
              fontSize: "1.2rem",
              marginBottom: "0.8rem",
            }}
          >
            Use cases
          </h2>
          <ul style={{ marginLeft: "1.1rem", color: "var(--silver)", lineHeight: 1.75 }}>
            {useCases.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>

        <article
          style={{
            border: "1px solid var(--crimson)",
            borderLeft: "4px solid var(--crimson)",
            borderRadius: "10px",
            background: "var(--surface)",
            padding: "1.35rem",
            marginBottom: "1rem",
          }}
        >
          <h2
            style={{
              fontFamily: "var(--font-head)",
              fontSize: "1.2rem",
              marginBottom: "0.8rem",
            }}
          >
            Next step
          </h2>
          <div className="seo-page-cta-stack" style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
            <Link className="btn-primary" href="/demo">
              Try Live Demo
            </Link>
            <Link className="btn-secondary" href="/pricing">
              View Pricing
            </Link>
            <a
              className="btn-secondary"
              href="mailto:info@aletheia-core.com?subject=Service Inquiry"
            >
              Book a Service
            </a>
          </div>
        </article>

        <article
          style={{
            border: "1px solid var(--border)",
            borderRadius: "10px",
            background: "var(--surface)",
            padding: "1.35rem",
            marginBottom: "1rem",
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
                <h3 style={{ color: "var(--white)", fontSize: "1rem", marginBottom: "0.35rem" }}>{entry.q}</h3>
                <p style={{ color: "var(--silver)", fontSize: "0.9rem", lineHeight: 1.6 }}>{entry.a}</p>
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
          }}
        >
          <h2 style={{ fontFamily: "var(--font-head)", fontSize: "1.2rem", marginBottom: "0.7rem" }}>
            Explore Aletheia Core
          </h2>
          <div className="seo-solution-explore-grid" style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "0.8rem" }}>
            {SEO_SOLUTIONS.map((entry) => (
              <Link
                key={entry.href}
                href={entry.href}
                style={{
                  border: "1px solid var(--border-hi)",
                  borderRadius: "8px",
                  background: "var(--surface-2)",
                  padding: "0.8rem",
                  textDecoration: "none",
                  opacity: entry.href === slug ? 0.82 : 1,
                }}
              >
                <h3
                  style={{
                    fontFamily: "var(--font-head)",
                    color: "var(--white)",
                    fontSize: "1rem",
                    marginBottom: "0.3rem",
                  }}
                >
                  {entry.title}
                </h3>
                <p style={{ color: "var(--muted)", fontSize: "0.9rem", lineHeight: 1.5 }}>
                  {entry.summary}
                </p>
              </Link>
            ))}
          </div>
        </article>
      </div>

      <script
        type="application/ld+json"
      >
        {JSON.stringify(faqSchema)}
      </script>
    </section>
  );
}
