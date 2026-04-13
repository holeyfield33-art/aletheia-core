import type { MetadataRoute } from "next";
import { URLS } from "@/lib/site-config";
import { BLOG_POSTS } from "@/app/blog/_posts";

export default function sitemap(): MetadataRoute.Sitemap {
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
      url: URLS.appBase,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 1.0,
    },
    {
      url: `${URLS.appBase}/demo`,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.9,
    },
    {
      url: `${URLS.appBase}/verify`,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.7,
    },
    {
      url: `${URLS.appBase}/status`,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 0.6,
    },
    {
      url: `${URLS.appBase}/pricing`,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.8,
    },
    {
      url: `${URLS.appBase}/docs`,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 0.8,
    },
    {
      url: `${URLS.appBase}/blog`,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 0.7,
    },
    {
      url: `${URLS.appBase}/changelog`,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 0.6,
    },
    {
      url: `${URLS.appBase}/cli`,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.5,
    },
    ...BLOG_POSTS.map((post) => ({
      url: `${URLS.appBase}/blog/${post.slug}`,
      lastModified: new Date(post.publishedAt),
      changeFrequency: "monthly" as const,
      priority: 0.6,
    })),
    ...legalPages.map((slug) => ({
      url: `${URLS.appBase}/legal/${slug}`,
      lastModified: new Date(),
      changeFrequency: "monthly" as const,
      priority: 0.4,
    })),
  ];
}
