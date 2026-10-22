import { strings } from "@/src/lib/i18n/strings";

export type ServiceTypeKey = "host" | "virtual_server" | "dedicated_server" | "cdn";
export type ResourceKey = "ram" | "cpu" | "disk" | "traffic";

export interface ServiceType {
  key: ServiceTypeKey;
  label: string;
}

/** The four fast "type of service" chips shown directly under the search box (PAGES.yaml). */
export const SERVICE_TYPES: ServiceType[] = [
  { key: "host", label: strings.serviceHost },
  { key: "virtual_server", label: strings.serviceVirtualServer },
  { key: "dedicated_server", label: strings.serviceDedicatedServer },
  { key: "cdn", label: strings.serviceCdn },
];

/**
 * Which resource choosers apply to a service type. CDN has no RAM/CPU/disk — only traffic
 * filtering applies (PAGES.yaml "just for host and servers no CDN (just traffic)").
 */
const RESOURCES_BY_TYPE: Record<ServiceTypeKey, ResourceKey[]> = {
  host: ["ram", "cpu", "disk", "traffic"],
  virtual_server: ["ram", "cpu", "disk", "traffic"],
  dedicated_server: ["ram", "cpu", "disk", "traffic"],
  cdn: ["traffic"],
};

export function resourcesForType(type: ServiceTypeKey): ResourceKey[] {
  return RESOURCES_BY_TYPE[type];
}

export const RESOURCE_LABELS: Record<ResourceKey, string> = {
  ram: strings.resourceRam,
  cpu: strings.resourceCpu,
  disk: strings.resourceDisk,
  traffic: strings.resourceTraffic,
};

/**
 * Ordered resource values (small → big). In production these come from the API; exported
 * here so the choosers share one ordering source.
 */
export const RESOURCE_OPTIONS: Record<ResourceKey, number[]> = {
  ram: [1, 2, 4, 8, 16, 32, 64],
  cpu: [1, 2, 4, 8, 16],
  disk: [20, 50, 100, 250, 500, 1000],
  traffic: [100, 500, 1000, 2000, 5000, 10000],
};

/**
 * Server locations per service type. The list is resolved dynamically from the selected
 * service type chip; in production it is fetched from the API (PAGES.yaml
 * "server locations — dynamically based on above filter buttons").
 */
export const SERVER_LOCATIONS: Record<ServiceTypeKey, string[]> = {
  host: ["تهران", "مشهد", "تبریز"],
  virtual_server: ["تهران", "فرانکفورت", "آمستردام"],
  dedicated_server: ["تهران", "فرانکفورت", "دبی"],
  cdn: ["ایران", "اروپا", "خاورمیانه"],
};
