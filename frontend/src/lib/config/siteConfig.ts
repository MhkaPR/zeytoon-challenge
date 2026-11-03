/**
 * Typed frontend runtime configuration.
 *
 * Values are served by the backend (`GET /api/v1/catalog/site-config`) and are editable from
 * the operator settings interface. The defaults below keep the SPA usable when the API is
 * unreachable and make component tests deterministic.
 */

export type ResourceKey = "ram" | "cpu" | "disk" | "traffic";

export interface SiteConfig {
  catalog: {
    priceMin: number;
    priceMax: number;
    priceStep: number;
    pageSizes: number[];
    defaultPageSize: number;
    resourceOptions: Record<ResourceKey, number[]>;
    companyFilterVisible: number;
  };
  ops: {
    siteRefreshMs: number;
    linksRefreshMs: number;
    captureDefaultDurationMs: number;
  };
  contact: {
    email: string;
    phone: string;
    address: string;
  };
  social: {
    instagram: string;
    telegram: string;
    linkedin: string;
    github: string;
  };
}

export const DEFAULT_SITE_CONFIG: SiteConfig = {
  catalog: {
    priceMin: 300000,
    priceMax: 1500000,
    priceStep: 50000,
    pageSizes: [8, 12, 20],
    defaultPageSize: 8,
    resourceOptions: {
      ram: [1, 2, 4, 8, 16, 32, 64],
      cpu: [1, 2, 4, 8, 16],
      disk: [20, 50, 100, 250, 500, 1000],
      traffic: [100, 500, 1000, 2000, 5000, 10000],
    },
    companyFilterVisible: 5,
  },
  ops: {
    siteRefreshMs: 8000,
    linksRefreshMs: 5000,
    captureDefaultDurationMs: 15000,
  },
  contact: {
    email: "support@torobhost.ir",
    phone: "021-12345678",
    address: "تهران، ایران",
  },
  social: {
    instagram: "https://instagram.com",
    telegram: "https://telegram.org",
    linkedin: "https://linkedin.com",
    github: "https://github.com",
  },
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

function asNumber(value: unknown, fallback: number): number {
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function asString(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function asNumberList(value: unknown, fallback: number[]): number[] {
  if (!Array.isArray(value)) return [...fallback];
  const parsed = value
    .map((item) => Number(item))
    .filter((item) => Number.isFinite(item));
  return parsed.length ? parsed : [...fallback];
}

function mergeResourceOptions(
  value: unknown,
  fallback: Record<ResourceKey, number[]>,
): Record<ResourceKey, number[]> {
  const raw = value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  return {
    ram: asNumberList(raw.ram, fallback.ram),
    cpu: asNumberList(raw.cpu, fallback.cpu),
    disk: asNumberList(raw.disk, fallback.disk),
    traffic: asNumberList(raw.traffic, fallback.traffic),
  };
}

/** Merge a partial API payload over the defaults so missing keys never break the UI. */
export function mergeSiteConfig(payload: unknown): SiteConfig {
  const raw = asRecord(payload);
  const catalog = asRecord(raw.catalog);
  const ops = asRecord(raw.ops);
  const contact = asRecord(raw.contact);
  const social = asRecord(raw.social);

  return {
    catalog: {
      priceMin: asNumber(catalog.priceMin, DEFAULT_SITE_CONFIG.catalog.priceMin),
      priceMax: asNumber(catalog.priceMax, DEFAULT_SITE_CONFIG.catalog.priceMax),
      priceStep: asNumber(catalog.priceStep, DEFAULT_SITE_CONFIG.catalog.priceStep),
      pageSizes: asNumberList(
        catalog.pageSizes,
        DEFAULT_SITE_CONFIG.catalog.pageSizes,
      ),
      defaultPageSize: asNumber(
        catalog.defaultPageSize,
        DEFAULT_SITE_CONFIG.catalog.defaultPageSize,
      ),
      resourceOptions: mergeResourceOptions(
        catalog.resourceOptions,
        DEFAULT_SITE_CONFIG.catalog.resourceOptions,
      ),
      companyFilterVisible: asNumber(
        catalog.companyFilterVisible,
        DEFAULT_SITE_CONFIG.catalog.companyFilterVisible,
      ),
    },
    ops: {
      siteRefreshMs: asNumber(
        ops.siteRefreshMs,
        DEFAULT_SITE_CONFIG.ops.siteRefreshMs,
      ),
      linksRefreshMs: asNumber(
        ops.linksRefreshMs,
        DEFAULT_SITE_CONFIG.ops.linksRefreshMs,
      ),
      captureDefaultDurationMs: asNumber(
        ops.captureDefaultDurationMs,
        DEFAULT_SITE_CONFIG.ops.captureDefaultDurationMs,
      ),
    },
    contact: {
      email: asString(contact.email, DEFAULT_SITE_CONFIG.contact.email),
      phone: asString(contact.phone, DEFAULT_SITE_CONFIG.contact.phone),
      address: asString(contact.address, DEFAULT_SITE_CONFIG.contact.address),
    },
    social: {
      instagram: asString(social.instagram, DEFAULT_SITE_CONFIG.social.instagram),
      telegram: asString(social.telegram, DEFAULT_SITE_CONFIG.social.telegram),
      linkedin: asString(social.linkedin, DEFAULT_SITE_CONFIG.social.linkedin),
      github: asString(social.github, DEFAULT_SITE_CONFIG.social.github),
    },
  };
}

/** Fetch the public runtime configuration, falling back to the built-in defaults. */
export async function getSiteConfig(): Promise<SiteConfig> {
  try {
    const response = await fetch(`${API_BASE}/api/v1/catalog/site-config`, {
      cache: "no-store",
    });
    if (!response.ok) return DEFAULT_SITE_CONFIG;
    return mergeSiteConfig(await response.json());
  } catch {
    return DEFAULT_SITE_CONFIG;
  }
}
