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

const API_ORIGIN = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function getPublishedPlans(params: Record<string, string> = {}) {
  const query = new URLSearchParams(params);
  try {
    const response = await fetch(`${API_ORIGIN}/api/v1/catalog/plans?${query}`, {
      next: { revalidate: 60 },
    });
    if (!response.ok) return [] as PublicPlan[];
    const data = (await response.json()) as { plans?: PublicPlan[] };
    return data.plans ?? [];
  } catch {
    return [] as PublicPlan[];
  }
}

export async function getRecentCompanies() {
  try {
    const response = await fetch(`${API_ORIGIN}/api/v1/catalog/companies/recent`, {
      next: { revalidate: 300 },
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
