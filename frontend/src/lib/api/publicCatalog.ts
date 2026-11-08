import { apiBaseUrl } from "@/src/lib/api/base";
import { createQueryString } from "@/src/lib/api/utils";
import type { ResourceKey } from "@/src/lib/config/siteConfig";

export interface PublicPlan {
  id: number;
  domain: string;
  company_name: string;
  plan_type: string;
  values: Record<string, string | number | boolean | null>;
  url?: string | null;
  published_at: string | null;
}

export interface RecentPublicCompany {
  domain: string;
  company_name: string;
  created_at: string;
}

export interface PlanFacets {
  companies: string[];
  operating_systems: string[];
  locations: string[];
  resources: Record<ResourceKey, number[]>;
  resource_units: Record<ResourceKey, string>;
}

export interface PlansPage {
  plans: PublicPlan[];
  count: number;
  page: number;
  pageSize: number;
  totalPages: number;
  facets: PlanFacets;
}

export interface PublicCompany {
  domain: string;
  company_name: string;
  plan_count: number;
}

export interface CompaniesPage {
  companies: PublicCompany[];
  count: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

const EMPTY_FACETS: PlanFacets = {
  companies: [],
  operating_systems: [],
  locations: [],
  resources: { ram: [], cpu: [], disk: [], traffic: [] },
  resource_units: { ram: "GB", cpu: "core", disk: "GB", traffic: "GB" },
};

export async function getPlansPage(
  params: Record<string, string | string[] | undefined> = {},
  options: { visitorId?: string } = {},
): Promise<PlansPage> {
  try {
    const query = await createQueryString(params);
    const headers: Record<string, string> = {};
    if (options.visitorId) headers["X-Visitor-Id"] = options.visitorId;
    const response = await fetch(`${apiBaseUrl()}/api/v1/catalog/plans?${query}`, {
      cache: "no-store",
      credentials: "include",
      headers,
    });
    if (!response.ok) {
      return { plans: [], count: 0, page: 1, pageSize: 0, totalPages: 1, facets: EMPTY_FACETS };
    }
    const payload = (await response.json()) as {
      data?: PublicPlan[];
      page?: {
        count?: number;
        page?: number;
        page_size?: number;
        total_pages?: number;
        facets?: Partial<PlanFacets>;
      };
    };
    const plans = payload.data ?? [];
    const page = payload.page ?? {};
    return {
      plans,
      count: page.count ?? plans.length,
      page: page.page ?? 1,
      pageSize: page.page_size ?? plans.length,
      totalPages: page.total_pages ?? 1,
      facets: {
        ...EMPTY_FACETS,
        ...page.facets,
        resources: {
          ...EMPTY_FACETS.resources,
          ...(page.facets?.resources ?? {}),
        },
        resource_units: {
          ...EMPTY_FACETS.resource_units,
          ...(page.facets?.resource_units ?? {}),
        },
      },
    };
  } catch {
    return { plans: [], count: 0, page: 1, pageSize: 0, totalPages: 1, facets: EMPTY_FACETS };
  }
}

export async function getPublishedPlans(
  params: Record<string, string | string[] | undefined> = {},
) {
  const first = await getPlansPage({ ...params, page: "1", page_size: "12" });
  if (first.totalPages <= 1) return first.plans;
  const remaining = await Promise.all(
    Array.from({ length: first.totalPages - 1 }, (_, index) =>
      getPlansPage({
        ...params,
        page: String(index + 2),
        page_size: "12",
      }),
    ),
  );
  return [first, ...remaining].flatMap((page) => page.plans);
}

export async function getSuggestedPlans(
  options: { visitorId?: string } = {},
): Promise<PublicPlan[]> {
  try {
    const headers: Record<string, string> = {};
    if (options.visitorId) headers["X-Visitor-Id"] = options.visitorId;
    const response = await fetch(`${apiBaseUrl()}/api/v1/catalog/plans/suggested`, {
      cache: "no-store",
      credentials: "include",
      headers,
    });
    if (!response.ok) return [];
    const payload = (await response.json()) as { data?: PublicPlan[] };
    return payload.data ?? [];
  } catch {
    return [];
  }
}

export async function getCompaniesPage({
  q = "",
  page = 1,
  pageSize = 12,
}: {
  q?: string;
  page?: number;
  pageSize?: number;
} = {}): Promise<CompaniesPage> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (q) params.set("q", q);
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/catalog/companies?${params}`, {
      cache: "no-store",
    });
    if (!response.ok) {
      return { companies: [], count: 0, page: 1, pageSize, totalPages: 1 };
    }
    const payload = (await response.json()) as {
      data?: PublicCompany[];
      page?: {
        count?: number;
        page?: number;
        page_size?: number;
        total_pages?: number;
      };
    };
    const companies = payload.data ?? [];
    const pageData = payload.page ?? {};
    return {
      companies,
      count: pageData.count ?? companies.length,
      page: pageData.page ?? 1,
      pageSize: pageData.page_size ?? pageSize,
      totalPages: pageData.total_pages ?? 1,
    };
  } catch {
    return { companies: [], count: 0, page: 1, pageSize, totalPages: 1 };
  }
}

export async function getRecentCompanies() {
  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/catalog/companies/recent`, {
      cache: "no-store",
    });
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
