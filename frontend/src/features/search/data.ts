export type ServiceKey = "host" | "virtual_server" | "dedicated_server" | "cdn";
export type ResultKind = "company" | "plan";

export interface SearchResult {
  id: string;
  kind: ResultKind;
  /** Primary line — a company or plan name. */
  title: string;
  /** Secondary line — provider and/or resource summary. */
  subtitle: string;
  service: ServiceKey;
  /** Optional image; the list falls back to a Material icon when absent. */
  image?: string;
}

export interface ServiceType {
  key: ServiceKey;
  /** Message key for the chip label; resolve it with the page translator. */
  labelKey: string;
}

/** The four fast service-type chips shown under the search field (PAGES.yaml chips). */
export const SERVICE_TYPES: ServiceType[] = [
  { key: "host", labelKey: "serviceHost" },
  { key: "virtual_server", labelKey: "serviceVirtualServer" },
  { key: "dedicated_server", labelKey: "serviceDedicatedServer" },
  { key: "cdn", labelKey: "serviceCdn" },
];

/** Which resource filters apply per service type; CDN is traffic-only. */
const RESOURCE_KEYS: Record<ServiceKey, Array<"ram" | "cpu" | "disk" | "traffic">> = {
  host: ["ram", "cpu", "disk", "traffic"],
  virtual_server: ["ram", "cpu", "disk", "traffic"],
  dedicated_server: ["ram", "cpu", "disk", "traffic"],
  cdn: ["traffic"],
};

export function resourceKeysFor(service: ServiceKey) {
  return RESOURCE_KEYS[service];
}

/** Message keys for the resource filter titles. */
export const RESOURCE_LABELS = {
  ram: "resourceRam",
  cpu: "resourceCpu",
  disk: "resourceDisk",
  traffic: "resourceTraffic",
} as const;

/** Ordered small → big; in production these come from the API. */
export const RESOURCE_VALUES = {
  ram: [1, 2, 4, 8, 16, 32, 64],
  cpu: [1, 2, 4, 8, 16],
  disk: [20, 50, 100, 250, 500, 1000],
  traffic: [100, 500, 1000, 2000, 5000, 10000],
} as const;

/** Server location message keys, resolved per service type from the API in production. */
export const SERVER_LOCATIONS: Record<ServiceKey, string[]> = {
  host: ["locTehran", "locMashhad", "locTabriz"],
  virtual_server: ["locTehran", "locFrankfurt", "locAmsterdam"],
  dedicated_server: ["locTehran", "locFrankfurt", "locDubai"],
  cdn: ["locIran", "locEurope", "locMiddleEast"],
};

/**
 * The local suggestion index. The rows live in the message catalog under ``searchIndex`` so
 * every suggestion is localized; pass ``translator.raw("searchIndex")`` in here.
 */
export function searchIndexFrom(raw: unknown): SearchResult[] {
  return Array.isArray(raw) ? (raw as SearchResult[]) : [];
}

/** Prefix/substring match over the localized index — the shape the API will keep. */
export function suggest(
  index: SearchResult[],
  query: string,
  service?: ServiceKey,
): SearchResult[] {
  const term = query.trim();
  if (!term) return [];
  return index.filter((result) => {
    if (service && result.service !== service) return false;
    return `${result.title} ${result.subtitle}`.includes(term);
  });
}
