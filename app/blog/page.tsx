import type { Metadata } from "next";
import { BLOG_POSTS } from "@/app/blog/_posts";
import { URLS } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "Engineering Blog",
  description:
    "Security engineering notes from the Aletheia Core team on policy enforcement, auditability, and agent runtime hardening.",
  alternates: { canonical: `${URLS.appBase}/blog` },
};

export default function BlogPage() {
  return (
    <div style={{ maxWidth: "960px", margin: "0 auto", padding: "3rem 2rem" }}>
      <h1
        style={{
          fontSize: "2.2rem",
          fontFamily: "var(--font-head)",
          fontWeight: 800,
          marginBottom: "0.5rem",
        }}
      >
        Engineering Blog
      </h1>
      <p
        style={{
          color: "var(--muted)",
          marginBottom: "2rem",
          maxWidth: "700px",
        }}
      >
        Practical security and reliability write-ups from Aletheia Core release
        work.
      </p>

      <div style={{ display: "grid", gap: "1rem" }}>
        {BLOG_POSTS.map((post) => (
          <article
            key={post.slug}
            style={{
              border: "1px solid var(--border)",
              borderRadius: "8px",
              background: "var(--surface)",
              padding: "1.25rem 1.1rem",
            }}
          >
            <p
              style={{
                color: "var(--muted)",
                fontFamily: "var(--font-mono)",
                fontSize: "0.75rem",
                marginBottom: "0.6rem",
              }}
            >
              {post.publishedAt}
            </p>
            <h2
              style={{
                marginBottom: "0.45rem",
                fontFamily: "var(--font-head)",
                fontSize: "1.3rem",
              }}
            >
              <a href={`/blog/${post.slug}`}>{post.title}</a>
            </h2>
            <p style={{ color: "var(--silver)", marginBottom: "0.75rem" }}>
              {post.description}
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
              {post.tags.map((tag) => (
                <span
                  key={tag}
                  style={{
                    fontSize: "0.72rem",
                    color: "var(--silver)",
                    border: "1px solid var(--border-hi)",
                    borderRadius: "999px",
                    padding: "0.2rem 0.55rem",
                    fontFamily: "var(--font-mono)",
                  }}
                >
                  {tag}
                </span>
              ))}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
