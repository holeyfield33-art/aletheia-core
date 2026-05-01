import type { MetadataRoute } from "next";
import { URLS, SEO_SOLUTIONS } from "@/lib/site-config";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: [
          "/",
          "/demo",
          "/verify",
          "/blog",
          "/changelog",
          "/cli",
          "/docs",
          "/pricing",
          ...SEO_SOLUTIONS.map((entry) => entry.href),
        ],
        disallow: ["/dashboard", "/api", "/auth"],
      },
    ],
    sitemap: `${URLS.appBase}/sitemap.xml`,
  };
}
