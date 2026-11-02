/**
 * Typed client for the company registration + panel API (contracts/companies-api.md).
 *
 * The panel surface, verification, plan eligibility, credit, and crawl all live in the
 * backend `companies` module under `/api/v1/companies`.
 */

import { AuthApiError, type ApiErrorBody } from "./auth";

// Empty base = same origin (Next proxies ``/api/*`` to the backend in development).
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

export type VerificationStatus = "pending" | "verified" | "rejected";
export type ChargeStatus = "charged" | "not_charged";

export interface Company {
  id: number;
  domain: string;
  company_name: string;
  representative_name: string;
  phone_number: string;
  internal_number: string;
  verification_status: VerificationStatus;
  charge_status: ChargeStatus;
  crawl_enabled: boolean;
  is_archived: boolean;
  unverified: boolean;
}

export interface StepProgress {
  step_key: string;
  order: number;
  state: string;
  completed: boolean;
}

export interface SwitcherEntry {
  id: number;
  company_name: string;
  verification_status: VerificationStatus;
  unverified: boolean;
}

export interface SwitcherPayload {
  companies: SwitcherEntry[];
  empty_state: boolean;
  message?: string;
}

export type PanelEntry =
  | { view: "full_panel"; company: Company }
  | {
      view: "continue_registration";
      company: Company;
      step_progress: StepProgress[];
      current_step: string | null;
      verification_status: VerificationStatus;
    };

export interface PlanEligibility {
  allowed: boolean;
  missing: string[];
  message?: string;
}

export interface CreditEntry {
  id: number;
  direction: "charge" | "decharge";
  amount: number;
  reason: string;
  reference: string;
  created_at: string;
}

export interface CompanyCredit {
  current_credit: number;
  currency: string;
  entries: CreditEntry[];
}

async function request<T>(
  path: string,
  accessToken: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
      ...(init?.headers ?? {}),
    },
    credentials: "include",
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = (data as ApiErrorBody).error;
    throw new AuthApiError(
      error?.code ?? "unknown_error",
      error?.message ?? "Something went wrong.",
      error?.fields ?? {},
    );
  }
  return data as T;
}

export function listCompanies(accessToken: string) {
  return request<{ companies: Company[] }>(
    "/api/v1/companies/",
    accessToken,
  );
}

export function getPanelSwitcher(accessToken: string) {
  return request<SwitcherPayload>(
    "/api/v1/companies/panel-switcher",
    accessToken,
  );
}

export function getPanelEntry(accessToken: string, companyId: number) {
  return request<PanelEntry>(
    `/api/v1/companies/${companyId}/panel-entry`,
    accessToken,
  );
}

export function getPlanEligibility(accessToken: string, companyId: number) {
  return request<PlanEligibility>(
    `/api/v1/companies/${companyId}/plan-eligibility`,
    accessToken,
  );
}

export function getCompanyCredit(accessToken: string, companyId: number) {
  return request<CompanyCredit>(`/api/v1/companies/${companyId}/credit`, accessToken);
}

export function setCrawlEnabled(accessToken: string, companyId: number, enabled: boolean) {
  return request<{ crawl_enabled: boolean; credit_unchanged: boolean }>(
    `/api/v1/companies/${companyId}/crawl`,
    accessToken,
    { method: "POST", body: JSON.stringify({ enabled }) },
  );
}

export function createCompany(
  accessToken: string,
  payload: {
    domain: string;
    company_name: string;
    representative_name: string;
    phone_number: string;
    internal_number?: string;
  },
) {
  return request<{ company: Company; step_progress: StepProgress[] }>(
    "/api/v1/companies/",
    accessToken,
    { method: "POST", body: JSON.stringify(payload) },
  );
}
