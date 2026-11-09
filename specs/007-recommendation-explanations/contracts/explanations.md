# Interface Contract: Recommendation Explanations

This feature adds one read-only HTTP endpoint to the existing `recommendations` module and
one frontend data shape. No existing contract changes.

## Endpoint

`GET /api/v1/recommendations/explanations`

- **Method / version**: `GET`, API v1. Registered on the recommendations router alongside
  `signals`.
- **Auth**: none required; behaves like the catalog read. Identity is taken from, in order,
  an authenticated session, the `X-Visitor-Id` header, or the `visitor_id` cookie — the same
  resolution used by `signals` and `catalog/plans/suggested`.
- **Side effects**: none visible to the client. Computation reads the **persisted** plan
  space (PostgreSQL) with a Redis read-through cache, and persists the viewer's explanation
  result on first computation so later calls do not recompute. Safe to call on every page
  load.
- **Backend rules conformance**: DRF only; no `APIView` (viewset + `@action` or a
  `GenericViewSet`); response produced by a serializer, never a hand-built dict; envelope
  `{"data": {...}}`; `snake_case` JSON.

### Request

No body and no required query parameters.

### Response `200`

```json
{
  "data": {
    "explanations": [
      {
        "plan_id": 1234,
        "has_textual": true,
        "matches": [
          { "category": "textual", "kind": "textual", "label": "semantic" },
          {
            "category": "technical",
            "kind": "technical_numeric",
            "name": "cpu",
            "unit": "core",
            "low": 2,
            "high": 4
          },
          {
            "category": "technical",
            "kind": "technical_categorical",
            "name": "country",
            "label": "Germany"
          }
        ]
      }
    ]
  }
}
```

### Field semantics

| Field | Type | Notes |
|-------|------|-------|
| `explanations` | array | 0..`RECOMMENDATION_MAX_INTEREST_CLUSTERS` entries, one per retained interest. |
| `plan_id` | int | Closest published plan for that interest; renderable against the existing plan payload. |
| `has_textual` | bool | True when a textual (title-category) match is among the selected features. |
| `matches` | array | 0..`RECOMMENDATION_EXPLANATION_FEATURE_COUNT` entries, ordered closest first. |
| `matches[].category` | `"textual"` \| `"technical"` | The two feature categories. |
| `matches[].kind` | enum | `textual` \| `technical_numeric` \| `technical_categorical`. |
| `matches[].name` | string | Technical attribute key (`cpu`, `ram`, `disk`, `traffic`, `price`) for numeric matches. |
| `matches[].unit` | string | Real unit for numeric matches (`core`, `GB`, `IRR`); omitted when unknown. |
| `matches[].low` / `high` | number | Reverted real-value range; `low <= high`; clamped to observed catalogue span. |
| `matches[].label` | string | Category name for textual/categorical matches. |

### Guarantees

- **Deterministic**: identical profile, space, and configuration produce byte-identical
  output (spec SC-005).
- **Bounded**: never more explanations than the cluster cap; never more matches than the
  configured count.
- **Non-leaking**: no normalized scores, dimension indexes, space versions, or internal ids
  appear in output (spec FR-012).
- **Degrades safely**: cold-start viewers get `{"explanations": []}`; outdated profiles get
  an empty list, never a 5xx.
- **Durable**: served from PostgreSQL when the cache is empty; a cache eviction never
  returns an empty or cold-computed result for a viewer who already has one.

### Errors

- `200` with empty `explanations` for no-interest, empty catalogue, or unmatched profile.
- Standard DRF `400/500` only for genuine infrastructure faults; explanation logic must not
  raise on missing attributes, empty titles, or dimension mismatches.

## Frontend contract

`frontend/src/lib/api/explanations.ts` exposes a typed
`getRecommendationExplanations({ visitorId })` returning the parsed payload. The suggested
plans surface builds a localized sentence from the `matches` using templates in
`frontend/src/lib/i18n/messages/fa.json`:

- textual match → a "you are interested in this category of products" sentence.
- technical numeric match → a sentence naming the attribute and the range with its unit.
- technical categorical match → a sentence naming the category.

The frontend only formats; it never reverts normalization or ranks features.
