import type { MetadataRoute } from "next";
import { URLS } from "@/lib/site-config";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: ["/", "/demo", "/verify"],
        disallow: ["/dashboard", "/api", "/auth"],
      },
    ],
    sitemap: `${URLS.appBase}/sitemap.xml`,
  };
}
