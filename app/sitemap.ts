import type { MetadataRoute } from "next";
import { URLS, SEO_SOLUTIONS } from "@/lib/site-config";
import { BLOG_POSTS } from "@/app/blog/_posts";

export default function sitemap(): MetadataRoute.Sitemap {
  const siteBase = URLS.landingPage;
  const legalPages = [
    "privacy",
    "terms",
    "acceptable-use",
    "billing",
    "security",
    "accessibility",
    "cookies",
  ];

  return [
    {
      url: siteBase,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 1.0,
    },
    {
      url: `${siteBase}/demo`,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.9,
    },
    {
      url: `${siteBase}/verify`,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.7,
    },
    {
      url: `${siteBase}/status`,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 0.6,
    },
    {
      url: `${siteBase}/pricing`,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.8,
    },
    {
      url: `${siteBase}/docs`,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 0.8,
    },
    {
      url: `${siteBase}/blog`,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 0.7,
    },
    {
      url: `${siteBase}/changelog`,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 0.6,
    },
    {
      url: `${siteBase}/cli`,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.5,
    },
    ...SEO_SOLUTIONS.map((entry) => ({
      url: `${siteBase}${entry.href}`,
      lastModified: new Date(),
      changeFrequency: "monthly" as const,
      priority: 0.72,
    })),
    ...BLOG_POSTS.map((post) => ({
      url: `${siteBase}/blog/${post.slug}`,
      lastModified: new Date(post.publishedAt),
      changeFrequency: "monthly" as const,
      priority: 0.6,
    })),
    ...legalPages.map((slug) => ({
      url: `${siteBase}/legal/${slug}`,
      lastModified: new Date(),
      changeFrequency: "monthly" as const,
      priority: 0.4,
    })),
  ];
}
