import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { BLOG_POSTS, getPostBySlug } from "@/app/blog/_posts";
import { MARKETING_ORIGIN } from "@/lib/site-config";

export function generateStaticParams() {
  return BLOG_POSTS.map((post) => ({ slug: post.slug }));
}

export function generateMetadata({
  params,
}: {
  params: { slug: string };
}): Metadata {
  const post = getPostBySlug(params.slug);
  if (!post) {
    return { title: "Post Not Found" };
  }

  const canonical = `${MARKETING_ORIGIN}/blog/${post.slug}`;
  return {
    title: post.title,
    description: post.description,
    alternates: { canonical },
    openGraph: {
      title: post.title,
      description: post.description,
      url: canonical,
      type: "article",
    },
  };
}

export default function BlogPostPage({ params }: { params: { slug: string } }) {
  const post = getPostBySlug(params.slug);
  if (!post) {
    notFound();
  }

  return (
    <article
      style={{ maxWidth: "780px", margin: "0 auto", padding: "3rem 2rem" }}
    >
      <p
        style={{
          color: "var(--muted)",
          fontFamily: "var(--font-mono)",
          fontSize: "0.78rem",
          marginBottom: "0.85rem",
        }}
      >
        {post.publishedAt}
      </p>
      <h1
        style={{
          fontFamily: "var(--font-head)",
          fontSize: "clamp(1.9rem, 4.8vw, 2.5rem)",
          lineHeight: 1.15,
          marginBottom: "0.7rem",
        }}
      >
        {post.title}
      </h1>
      <p style={{ color: "var(--silver)", marginBottom: "1.7rem" }}>
        {post.description}
      </p>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "0.5rem",
          marginBottom: "2rem",
        }}
      >
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

      {post.sections.map((section) => (
        <section key={section.heading} style={{ marginBottom: "1.8rem" }}>
          <h2
            style={{
              fontFamily: "var(--font-head)",
              fontSize: "1.3rem",
              marginBottom: "0.65rem",
            }}
          >
            {section.heading}
          </h2>
          {section.body.map((paragraph, index) => (
            <p
              key={`${section.heading}-${index}`}
              style={{ color: "var(--silver)", marginBottom: "0.75rem" }}
            >
              {paragraph}
            </p>
          ))}
        </section>
      ))}

      <hr
        style={{
          border: "none",
          borderTop: "1px solid var(--border)",
          margin: "2rem 0",
        }}
      />
      <p style={{ color: "var(--muted)", fontSize: "0.9rem" }}>
        More articles: <a href="/blog">blog index</a>
      </p>
    </article>
  );
}
