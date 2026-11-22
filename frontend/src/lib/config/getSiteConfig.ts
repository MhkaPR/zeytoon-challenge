"use cache";

import { apiBaseUrl } from "@/src/lib/api/base";

import {
  DEFAULT_SITE_CONFIG,
  mergeSiteConfig,
  type SiteConfig,
} from "./siteConfig";

/** Fetch the public runtime configuration, falling back to the built-in defaults. */
export async function getSiteConfig(): Promise<SiteConfig> {
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/catalog/site-config`, {
      next: { revalidate: 300 },
    });
    if (!response.ok) return DEFAULT_SITE_CONFIG;
    return mergeSiteConfig(await response.json());
  } catch {
    return DEFAULT_SITE_CONFIG;
  }
}
