/**
 * Typed client for the company registration + panel API (contracts/companies-api.md).
 *
 * The panel surface, verification, plan eligibility, and link submission all live in the
 * backend `companies` module under `/api/v1/companies`.
 */

import { AuthApiError, type ApiErrorBody } from "./auth";

// Empty base = same origin (Next proxies ``/api/*`` to the backend in development).
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

export type VerificationStatus = "pending" | "verified" | "rejected";

export interface Company {
  id: number;
  domain: string;
  company_name: string;
  representative_name: string;
  phone_number: string;
  internal_number: string;
  verification_status: VerificationStatus;
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

export function addCompanyLinks(accessToken: string, companyId: number, urls: string[]) {
  return request<{ links: { id: number; url: string }[] }>(
    `/api/v1/companies/${companyId}/links`,
    accessToken,
    { method: "POST", body: JSON.stringify({ urls }) },
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
