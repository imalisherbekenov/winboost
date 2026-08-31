import type { MetadataRoute } from "next";

export const dynamic = "force-static";

const pages = ["", "/privacy", "/terms", "/contacts"];

export default function sitemap(): MetadataRoute.Sitemap {
  return pages.map((path, index) => ({
    url: `https://winboost.app${path}`,
    lastModified: "2026-08-31",
    changeFrequency: index === 0 ? "monthly" : "yearly",
    priority: index === 0 ? 1 : 0.5,
  }));
}
