import {CatalogFilterValues, CatalogSearchParams} from "@/src/features/home/HomePlanCatalog";
import {createQueryString} from "@/src/lib/api/utils";
import {SearchParams} from "next/dist/server/request/search-params";

export interface PublicPlan {
  id: number;
  domain: string;
  company_name: string;
  plan_type: string;
  values: Record<string, string | number | boolean | null>;
  published_at: string | null;
}

export interface RecentPublicCompany {
  domain: string;
  company_name: string;
  created_at: string;
}

// Empty base = same origin. In development Next proxies ``/api/*`` to the backend (see
// next.config.ts), so the browser talks to the API without a cross-origin round trip.
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

export async function getPublishedPlans(params: SearchParams) {
  try {
    const query = await createQueryString(params)
    const response = await fetch(`${API_BASE}/api/v1/catalog/plans?${query}`);
    if (!response.ok) return [] as PublicPlan[];
    const data = (await response.json()) as { plans?: PublicPlan[] };
    return data.plans ?? [];
  } catch {
    return [] as PublicPlan[];
  }
}

export async function getRecentCompanies() {
  try {
    const response = await fetch(`${API_BASE}/api/v1/catalog/companies/recent`);
    if (!response.ok) return [] as RecentPublicCompany[];
    const data = (await response.json()) as { companies?: RecentPublicCompany[] };
    return data.companies ?? [];
  } catch {
    return [] as RecentPublicCompany[];
  }
}

export function planName(plan: PublicPlan) {
  return String(plan.values.plan_name ?? plan.values.name ?? plan.plan_type);
}

export function displayField(key: string, labels?: Record<string, string>) {
  return labels?.[key] ?? key.replaceAll("_", " ");
}

export function ensureHttps(url: string) {
  if (!url) return '';
  if (/^https?:\/\//i.test(url)) return url;
  return `https://${url}`;
}
