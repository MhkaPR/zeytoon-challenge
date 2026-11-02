import { strings } from "@/src/lib/i18n/strings";

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
  label: string;
}

/** The four fast service-type chips shown under the search field (PAGES.yaml chips). */
export const SERVICE_TYPES: ServiceType[] = [
  { key: "host", label: strings.serviceHost },
  { key: "virtual_server", label: strings.serviceVirtualServer },
  { key: "dedicated_server", label: strings.serviceDedicatedServer },
  { key: "cdn", label: strings.serviceCdn },
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

export const RESOURCE_LABELS = {
  ram: strings.resourceRam,
  cpu: strings.resourceCpu,
  disk: strings.resourceDisk,
  traffic: strings.resourceTraffic,
} as const;

/** Ordered small → big; in production these come from the API. */
export const RESOURCE_VALUES = {
  ram: [1, 2, 4, 8, 16, 32, 64],
  cpu: [1, 2, 4, 8, 16],
  disk: [20, 50, 100, 250, 500, 1000],
  traffic: [100, 500, 1000, 2000, 5000, 10000],
} as const;

/** Server locations, resolved per service type from the API in production. */
export const SERVER_LOCATIONS: Record<ServiceKey, string[]> = {
  host: ["تهران", "مشهد", "تبریز"],
  virtual_server: ["تهران", "فرانکفورت", "آمستردام"],
  dedicated_server: ["تهران", "فرانکفورت", "دبی"],
  cdn: ["ایران", "اروپا", "خاورمیانه"],
};

/** Local suggestion index; replaced by the search API when that feature lands. */
export const SEARCH_INDEX: SearchResult[] = [
  {
    id: "c-1",
    kind: "company",
    title: "میزبان سرور پارس",
    subtitle: "ارائه دهنده هاست و سرور اختصاصی",
    service: "host",
  },
  {
    id: "p-1",
    kind: "plan",
    title: "هاست لینوکس حرفه‌ای",
    subtitle: "رم ۴ گیگابایت · پردازنده ۲ هسته",
    service: "host",
  },
  {
    id: "p-2",
    kind: "plan",
    title: "سرور مجازی ابری",
    subtitle: "رم ۱۶ گیگابایت · پردازنده ۸ هسته",
    service: "virtual_server",
  },
  {
    id: "c-2",
    kind: "company",
    title: "ابر رایان",
    subtitle: "ارائه دهنده سرور مجازی و اختصاصی",
    service: "virtual_server",
  },
  {
    id: "p-3",
    kind: "plan",
    title: "سرور اختصاصی پرقدرت",
    subtitle: "رم ۶۴ گیگابایت · پردازنده ۱۶ هسته",
    service: "dedicated_server",
  },
  {
    id: "p-4",
    kind: "plan",
    title: "شبکه توزیع محتوا",
    subtitle: "ترافیک ۲ ترابایت",
    service: "cdn",
  },
];

/** Prefix/substring match over the local index — the shape the API will keep. */
export function suggest(query: string, service?: ServiceKey): SearchResult[] {
  const term = query.trim();
  if (!term) return [];
  return SEARCH_INDEX.filter((result) => {
    if (service && result.service !== service) return false;
    return `${result.title} ${result.subtitle}`.includes(term);
  });
}
