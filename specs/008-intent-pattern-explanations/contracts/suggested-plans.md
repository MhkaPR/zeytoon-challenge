# Interface Contract: Suggested Plans with Intent Explanations

This feature extends the existing suggested-plans endpoint and removes the separate
explanation endpoint. No new HTTP route is added.

## Endpoint

`GET /api/v1/catalog/plans/suggested`

- **Auth**: none required; identity resolves from the authenticated user, `X-Visitor-Id`
  header, or `visitor_id` cookie, matching the existing behavior.
- **Side effects**: none persisted. The response is derived from the cached recommendation
  space, the viewer profile, and the viewer's destination-visit signals.
- **Backend rules**: DRF viewset action; response produced by serializers; `snake_case`
  JSON.

## Response `200`

```json
{
  "data": [
    {
      "id": 395,
      "domain": "example.com",
      "company_name": "Example Co",
      "plan_type": "hosting",
      "values": { "plan_name": "Cloud 4", "price_amount": 1200000 },
      "url": "https://example.com/plan/395",
      "published_at": "2026-11-10T10:00:00Z"
    }
  ],
  "explanations": [
    {
      "cluster_id": 0,
      "representative_plan_id": 395,
      "plan_ids": [395, 401],
      "intent": "value",
      "direction": "positive",
      "message": "دنبال بهترین نسبت امکانات به قیمت هستی؟",
      "confidence": { "lift": 4.2, "p": 0.001, "mcc": 0.62 }
    },
    {
      "cluster_id": 1,
      "representative_plan_id": 210,
      "plan_ids": [210],
      "intent": "exploring",
      "direction": null,
      "message": "در حال کاوش گزینه‌های مختلف هستی؟",
      "confidence": null
    }
  ]
}
```

## Field semantics

| Field | Type | Notes |
|-------|------|-------|
| `data` | array | Existing suggested plan payload; unchanged. |
| `explanations` | array | One entry per interest cluster, in cluster order. |
| `explanations[].cluster_id` | int | Cluster index. |
| `explanations[].representative_plan_id` | int or null | Closest plan in the candidate set; null only when no candidate exists. |
| `explanations[].plan_ids` | array[int] | Suggested plans assigned to this cluster; rendered as the cluster's plan list. |
| `explanations[].intent` | enum | `cheap`, `value`, `spec_heavy`, `premium`, or `exploring`. |
| `explanations[].direction` | enum or null | `positive`, `negative`, or null for `exploring`. |
| `explanations[].message` | string | Persian intent sentence; never contains a numeric range. |
| `explanations[].confidence` | object or null | `{lift, p, mcc}` for real intents; null for `exploring`. |
| `explanations` order | array | Cluster order; repeated intents remain separate entries. |

## Guarantees

- **Per-cluster independence**: cluster positions are never averaged.
- **Exploring is fallback-only**: it is never scored as a competitor.
- **Deterministic**: identical profile, space version, and configuration produce
  byte-identical explanations.
- **No attribute leakage**: messages describe intent and contain no numeric range tied to a
  feature bin center.
- **Bounded**: at most the configured maximum number of clusters; exactly one explanation
  per cluster.
- **Degrades safely**: cold-start, random-click, empty-catalog, and stale-profile requests
  return `exploring` or an empty explanation list without a 5xx.

## Removed contract

`GET /api/v1/recommendations/explanations` is removed. The frontend no longer fetches a
separate explanation payload; it reads `primary_explanation` from the suggested-plans
response.

## Frontend contract

`frontend/src/lib/api/intentExplanations.ts` exposes the typed
`ClusterIntentExplanation` shape. `SuggestedPlans` renders one row per explanation,
including repeated intents, and does not build numeric attribute ranges.
