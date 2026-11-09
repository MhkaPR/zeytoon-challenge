import { apiBaseUrl } from "@/src/lib/api/base";

export type SignalKind =
  | "destination_visit"
  | "details_view"
  | "search_impression";

/** Fire-and-forget interest signal; never blocks navigation. */
export function sendSignal(
  kind: SignalKind,
  planIds: number[],
  query?: string,
  visitorId?: string,
): void {
  if (typeof window === "undefined" || planIds.length === 0) return;
  const body: Record<string, unknown> = { kind, plan_ids: planIds };
  if (query) body.query = query;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (visitorId) headers["X-Visitor-Id"] = visitorId;
  void fetch(`${apiBaseUrl()}/api/v1/recommendations/signals`, {
    method: "POST",
    headers,
    credentials: "include",
    keepalive: true,
    body: JSON.stringify(body),
  }).catch(() => undefined);
}
