/**
 * Resolve the API origin for the current runtime.
 *
 * In the browser an empty base keeps requests same-origin (Next proxies `/api/*`). During
 * server rendering a relative URL cannot be fetched, so use the backend origin directly.
 */
export function apiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (configured) return configured;
  if (typeof window === "undefined") {
    return process.env.API_INTERNAL_BASE_URL ?? "http://localhost:8000";
  }
  return "";
}
