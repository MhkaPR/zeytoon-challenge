/**
 * Typed client for the operator console API (contracts/ops-console-api.md).
 *
 * Every console endpoint lives under `/api/v1/ops/`. A missing access token is an error the
 * caller surfaces; the console shell only renders for an authenticated operator.
 */

import { AuthApiError, type ApiErrorBody } from "./auth";

// Empty base = same origin (Next proxies ``/api/*`` to the backend in development).
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

async function request<T>(
  path: string,
  accessToken: string | null,
  init?: RequestInit,
): Promise<T> {
  const headers: Record<string, string> = {
    ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
    ...((init?.headers as Record<string, string>) ?? {}),
  };
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
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

export interface ApprovalQueueEntry {
  company_id: number;
  company_name: string;
  representative_name: string;
  domain: string;
  phone_masked: string;
  registered_at: string;
  duplicate_domain_warning: boolean;
  duplicate_of: number[];
}

export interface Site {
  id: number;
  company_id: number;
  domain: string;
  has_sitemap: boolean;
  sitemap_url: string;
  maintenance_state: string;
  onboarded_at: string | null;
}

export interface Link {
  id: number;
  site_id: number;
  url: string;
  source: string;
  review_state: string;
  pipeline_stage: string;
  failure_rate: number;
  current_trace_id: number | null;
}

export interface CaptureSession {
  id: number;
  link_id: number;
  mode: string;
  state: string;
  local_path: string;
  duration_ms: number | null;
  error: string;
  trace_id: number | null;
}

export interface TableColumn {
  id: number;
  column_id: string;
  label: string;
  path: string;
  atype: string;
  slot: string;
  coverage: number;
  row_count: number;
  labels: string[];
}

export interface ExtractedTable {
  id: number;
  score: number;
  row_count: number;
  column_count: number;
  parent: string;
  meta: Record<string, unknown>;
  title: string;
  purpose: string;
  columns: TableColumn[];
  rows: { row_index: number; cells: Record<string, string> }[];
}

export interface PlanSchemaField {
  key: string;
  label: string;
  kind: string;
  required: boolean;
  unit_family: string | null;
  values: string[];
}

export interface PlanType {
  key: string;
  label: string;
  fields: PlanSchemaField[];
}

export interface RecipeBinding {
  schema_field_key: string;
  source_table_id: number | null;
  source_column_id: number | null;
  selector: string;
  formula: string;
  aggregation?: string;
}

export interface Recipe {
  id: number;
  link_id: number;
  site_id: number;
  plan_type: string;
  version: number;
  is_complete: boolean;
  bindings: RecipeBinding[];
}

export interface ReplayRun {
  id: number;
  link_id: number;
  recipe_id: number | null;
  state: string;
  before_trace_id: number | null;
  after_trace_id: number | null;
  diff_summary: Record<string, unknown>;
  diff_applied: boolean;
  stats_applied: number;
  stats_skipped: number;
  stats_failed: number;
  failures: unknown[];
  started_at: string | null;
  finished_at: string | null;
}

export interface FailureAlert {
  id: number;
  link_id: number;
  state: string;
  failure_rate: number;
  raised_at: string | null;
  resolved_at: string | null;
}

export interface Notification {
  id: number;
  event_type: string;
  severity: string;
  subject: string;
  body: string;
  related_object: string;
  is_resolved: boolean;
  created_at: string;
}

export interface Recipient {
  id: number;
  user_id: number;
  name: string;
  is_active: boolean;
  user_phone: string;
}

// --- US1 approvals ---------------------------------------------------------
export function getApprovalQueue(token: string | null) {
  return request<{ results: ApprovalQueueEntry[]; count: number }>(
    "/api/v1/ops/approvals",
    token,
  );
}

export function decideVerification(
  token: string | null,
  companyId: number,
  outcome: "approved" | "not_approved",
  note = "",
) {
  return request<Record<string, unknown>>(
    `/api/v1/ops/companies/${companyId}/verification-decisions`,
    token,
    { method: "POST", body: JSON.stringify({ outcome, note }) },
  );
}

// --- US2 sites + links -----------------------------------------------------
export function createSite(token: string | null, companyId: number) {
  return request<{ site: Site }>("/api/v1/ops/sites", token, {
    method: "POST",
    body: JSON.stringify({ company_id: companyId }),
  });
}

export function listSites(token: string | null) {
  return request<{
    results: (Site & { links_count: number })[];
    count: number;
  }>("/api/v1/ops/sites", token);
}

export function getSite(token: string | null, siteId: number) {
  return request<{ site: Site; links: Link[] }>(
    `/api/v1/ops/sites/${siteId}`,
    token,
  );
}

export function discoverLinks(token: string | null, siteId: number) {
  return request<{ has_sitemap: boolean; sitemap_url: string; discovered: number }>(
    `/api/v1/ops/sites/${siteId}/discover-links`,
    token,
    { method: "POST" },
  );
}

export function getSiteLinks(token: string | null, siteId: number) {
  return request<{ site_id: number; links: Link[] }>(
    `/api/v1/ops/sites/${siteId}/links`,
    token,
  );
}

export function addManualLinks(token: string | null, siteId: number, urls: string[]) {
  return request<{ discovered: number }>(`/api/v1/ops/sites/${siteId}/links`, token, {
    method: "POST",
    body: JSON.stringify({ urls }),
  });
}

export function reviewLinks(
  token: string | null,
  siteId: number,
  keepIds: number[],
  removeIds: number[],
) {
  return request<{ kept: number; removed: number; maintenance_state: string }>(
    `/api/v1/ops/sites/${siteId}/links/review`,
    token,
    { method: "POST", body: JSON.stringify({ keep_ids: keepIds, remove_ids: removeIds }) },
  );
}

// --- US3 capture -----------------------------------------------------------
export function startCapture(
  token: string | null,
  linkId: number,
  mode = "interactive",
  durationMs?: number,
) {
  return request<{ capture: CaptureSession }>(
    `/api/v1/ops/links/${linkId}/captures`,
    token,
    { method: "POST", body: JSON.stringify({ mode, duration_ms: durationMs ?? null }) },
  );
}

export function uploadTrace(token: string | null, captureSessionId: number, file: File) {
  const form = new FormData();
  form.append("file", file);
  return request<{ trace: Record<string, unknown>; capture: CaptureSession }>(
    `/api/v1/ops/captures/${captureSessionId}/trace`,
    token,
    { method: "POST", body: form },
  );
}

export function uploadLocalTrace(
  token: string | null,
  captureSessionId: number,
  localPath: string,
) {
  return request<{ trace: Record<string, unknown>; capture: CaptureSession }>(
    `/api/v1/ops/captures/${captureSessionId}/trace`,
    token,
    { method: "POST", body: JSON.stringify({ local_path: localPath }) },
  );
}

export interface DomtrackHealth {
  reachable: boolean;
  base_url: string;
  name?: string | null;
  version?: string | null;
  trace_dir?: string | null;
  status?: number;
  error?: string;
}

export function getDomtrackHealth(token: string | null) {
  return request<DomtrackHealth>("/api/v1/ops/domtrack/health", token);
}

export function getActiveCapture(token: string | null) {
  return request<{ capture: CaptureSession | null; link_url: string | null }>(
    "/api/v1/ops/captures/active",
    token,
  );
}

export function failCapture(token: string | null, captureSessionId: number, error: string) {
  return request<Record<string, unknown>>(
    `/api/v1/ops/captures/${captureSessionId}/fail`,
    token,
    { method: "POST", body: JSON.stringify({ error }) },
  );
}

// --- US4 extraction --------------------------------------------------------
export function extractTables(token: string | null, linkId: number) {
  return request<{ table_count: number; pipeline_stage: string }>(
    `/api/v1/ops/links/${linkId}/extractions`,
    token,
    { method: "POST" },
  );
}

export function getTables(token: string | null, linkId: number) {
  return request<{
    link_id: number;
    site_id: number;
    url: string;
    pipeline_stage: string;
    current_trace_id: number | null;
    tables: ExtractedTable[];
  }>(`/api/v1/ops/links/${linkId}/tables`, token);
}

// --- US5 labeling + settings ----------------------------------------------
export function labelTables(token: string | null, linkId: number) {
  return request<Record<string, unknown>>(
    `/api/v1/ops/links/${linkId}/labeling`,
    token,
    { method: "POST" },
  );
}

export function getSettings(token: string | null) {
  return request<Record<string, unknown>>("/api/v1/ops/settings", token);
}

export function updateSettings(token: string | null, values: Record<string, unknown>) {
  return request<Record<string, unknown>>("/api/v1/ops/settings", token, {
    method: "PUT",
    body: JSON.stringify({ values }),
  });
}

export function getLlmCeiling(token: string | null) {
  return request<Record<string, unknown>>("/api/v1/ops/llm-cost-ceiling", token);
}

export function setLlmCeiling(
  token: string | null,
  ceilingAmount: number | null,
  period = "monthly",
) {
  return request<Record<string, unknown>>("/api/v1/ops/llm-cost-ceiling", token, {
    method: "PUT",
    body: JSON.stringify({ ceiling_amount: ceilingAmount, period }),
  });
}

// --- US6 mapping -----------------------------------------------------------
export function getPlanSchema(token: string | null) {
  return request<{ plan_types: PlanType[] }>("/api/v1/ops/plan-schema", token);
}

export function getRecipe(token: string | null, linkId: number) {
  return request<{
    link_id: number;
    pipeline_stage: string;
    recipe: Recipe | null;
    tables: ExtractedTable[];
  }>(`/api/v1/ops/links/${linkId}/recipe`, token);
}

export function saveRecipe(
  token: string | null,
  linkId: number,
  planType: string,
  bindings: RecipeBinding[],
) {
  return request<{ recipe: Recipe; link: { pipeline_stage: string } }>(
    `/api/v1/ops/links/${linkId}/recipe`,
    token,
    { method: "PUT", body: JSON.stringify({ plan_type: planType, bindings }) },
  );
}

// --- US7 cleaning + publishing --------------------------------------------
export function cleanLink(token: string | null, linkId: number) {
  return request<CleaningResult>(`/api/v1/ops/links/${linkId}/cleaning`, token, {
    method: "POST",
  });
}

export interface CleaningRecord {
  natural_key: string;
  plan_type: string;
  values: Record<string, unknown>;
  exceptions: Record<string, string>;
}

export interface CleaningResult {
  link_id: number;
  plan_type: string;
  recipe_id: number;
  cleaned_records: number;
  exception_count: number;
  records: CleaningRecord[];
}

export interface PublishResult {
  link_id: number;
  published: number;
  exception_count: number;
  pipeline_stage: string;
}

export function publishLink(token: string | null, linkId: number) {
  return request<PublishResult>(`/api/v1/ops/links/${linkId}/publish`, token, {
    method: "POST",
  });
}

// --- US8 replay + alerts ---------------------------------------------------
export function listReplayRuns(token: string | null, linkId?: number) {
  const suffix = linkId ? `?link_id=${linkId}` : "";
  return request<{ results: ReplayRun[]; count: number }>(
    `/api/v1/ops/replay-runs${suffix}`,
    token,
  );
}

export function createReplayRuns(
  token: string | null,
  payload: { link_ids?: number[]; site_id?: number } = {},
) {
  return request<{ results: Record<string, unknown>[]; count: number }>(
    "/api/v1/ops/replay-runs/create",
    token,
    { method: "POST", body: JSON.stringify(payload) },
  );
}

export function getLinkFailure(token: string | null, linkId: number) {
  return request<{
    link_id: number;
    pipeline_stage: string;
    failure_rate: number;
    threshold: number;
    window_runs: number;
    last_replay_at: string | null;
    open_alert: FailureAlert | null;
    recent_runs: ReplayRun[];
  }>(`/api/v1/ops/links/${linkId}/failure`, token);
}

export function rerunLink(token: string | null, linkId: number) {
  return request<{ pipeline_stage: string; previous_stage: string }>(
    `/api/v1/ops/links/${linkId}/rerun`,
    token,
    { method: "POST" },
  );
}

export function listAlerts(token: string | null, state?: string) {
  const suffix = state ? `?state=${state}` : "";
  return request<{ results: FailureAlert[]; count: number }>(
    `/api/v1/ops/alerts${suffix}`,
    token,
  );
}

// --- notifications ---------------------------------------------------------
export function listNotifications(token: string | null) {
  return request<{ results: Notification[]; count: number }>(
    "/api/v1/ops/notifications",
    token,
  );
}

export function listRecipients(token: string | null) {
  return request<{ results: Recipient[]; count: number }>(
    "/api/v1/ops/notification-recipients",
    token,
  );
}

export function addRecipient(token: string | null, userId: number, name = "") {
  return request<Recipient>("/api/v1/ops/notification-recipients", token, {
    method: "POST",
    body: JSON.stringify({ user_id: userId, name }),
  });
}

export function deactivateRecipient(token: string | null, recipientId: number) {
  return request<Recipient>(
    `/api/v1/ops/notification-recipients/${recipientId}/deactivate`,
    token,
    { method: "POST" },
  );
}

export function getMetrics(token: string | null) {
  return request<Record<string, unknown>>("/api/v1/ops/metrics", token);
}
