import type { MetadataRoute } from "next";
import { URLS } from "@/lib/site-config";

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
    ...legalPages.map((slug) => ({
      url: `${URLS.appBase}/legal/${slug}`,
      lastModified: new Date(),
      changeFrequency: "monthly" as const,
      priority: 0.4,
    })),
  ];
}
