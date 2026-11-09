# API Contract: Recommendations & Related Plans

**Feature**: `005-related-plans-sort`
**Date**: 2026-11-06

This contract covers the one new client-facing endpoint, the catalogue sort behaviour
change, the identity headers used between the Next.js server and Django, and the
sign-in hand-off that deliberately has no public endpoint. All responses use the
project envelope (`{"data": ...}` for single objects, `{"data": [...], "page": {...}}`
for collections) and `snake_case` fields.

## 1. Identity

| Header / cookie | Direction | Purpose |
|---|---|---|
| `visitor_id` cookie | browser → Next.js | Opaque random device identifier, httpOnly, `SameSite=Lax`, `Secure` in production, ~180-day max age. Issued by Next middleware. |
| `x-visitor-id` request header | Next middleware → server components | Carries the current request's visitor id so the first render is already personalised. |
| `X-Visitor-Id` request header | Next.js server → Django | Forwarded by `getPlansPage` only when rendering on the server. Django reads this for ranking. |
| `visitor_id` cookie | browser → Django | Sent automatically on same-origin signal requests (through the `/api/*` proxy). Django reads this for signal writes. |

Rules:

- Django never accepts a client-supplied identity for the sign-in hand-off.
- The visitor id is validated as a UUID; an invalid or missing value yields the
  cold-start order and no signal persistence.
- When the request is authenticated, account identity takes precedence over the device
  identity for both ranking and signals.

## 2. `GET /api/v1/catalog/plans` (modified)

The existing catalogue endpoint gains a new meaning for the default sort and accepts the
visitor identity header.

### Query parameters (unchanged except `sort`)

| Parameter | Values | Notes |
|---|---|---|
| `sort` | omitted, `default`, `price`, `expensive` | `omitted`/`default` now means related (was newest-first). `price` and `expensive` keep their current semantics. |
| `type`, `providers`, `os`, `location`, `ram`, `cpu`, `disk`, `traffic`, `q`, `domain`, `page`, `page_size` | unchanged | Filters narrow the candidate set before ranking (FR-011, FR-021). |

### Behaviour

- `sort=price` / `sort=expensive`: unchanged SQL ordering; no personalisation; no
  requirement for the visitor header.
- Related sort: filter first, rank the full matching set, then paginate. Order is
  `(distance, -published_at, id)` so ties are stable and pages do not repeat plans
  (FR-012, FR-013).
- Cold start (no profile, no signals): deterministic masked-mean prior, identical for
  every viewer without interest (FR-020).
- A profile whose `space_version` does not match the current space is treated as empty
  rather than erroring.

### Response

Unchanged envelope and `PublicPlanSerializer` fields. Ordering differs only under the
related sort.

```json
{
  "data": [
    {
      "id": 42,
      "domain": "example.com",
      "company_name": "Example Co",
      "plan_type": "hosting",
      "values": { "price_amount": 1000, "ram_amount": 4 },
      "url": "https://example.com/plans/42",
      "published_at": "2026-11-01T10:00:00Z"
    }
  ],
  "page": { "count": 120, "page": 1, "page_size": 12, "total_pages": 10, "facets": { } }
}
```

## 3. `POST /api/v1/recommendations/signals` (new)

The only client-initiated recommendation action.

### Request

```json
{
  "kind": "destination_visit",
  "plan_ids": [42],
  "query": null
}
```

| Field | Type | Rules |
|---|---|---|
| `kind` | string | Required. One of `destination_visit`, `details_view`, `search_impression`. |
| `plan_ids` | list[int] | Required, non-empty. One id for a visit or details view; the first page of results for a search impression. |
| `query` | string | Optional; required when `kind` is `search_impression`. Trimmed, length-limited. |

### Behaviour

- Identity is resolved server-side: authenticated request → account profile; otherwise
  the `visitor_id` cookie → device profile.
- If the device profile was tombstoned by a sign-in, the signal is applied to the linked
  account profile.
- `search_impression` applies one combined update using the centroid of the supplied
  candidates; other kinds apply one update per plan id.
- The signal is throttled per identity and per source; signals beyond the configured
  per-minute cap are ignored and reported in the response but are not an error.
- Signal weight is copied from the configured weights at recording time.

### Response

```json
{
  "data": {
    "accepted": 1,
    "ignored": 0,
    "profile": "visitor"
  }
}
```

| Field | Type | Notes |
|---|---|---|
| `accepted` | int | Number of signals absorbed. |
| `ignored` | int | Number dropped by the cap or by unknown plan ids. |
| `profile` | string | `visitor`, `user`, or `none` when no identity was available. |

### Errors

| Status | Code | When |
|---|---|---|
| 400 | `validation_error` | Missing/empty `plan_ids`, unknown `kind`, or missing `query` for a search impression. |
| 404 | `plan_not_found` | A supplied plan id does not exist among published records. |
| 429 | `rate_limited` | Throttle exceeded. |

## 4. Sign-in hand-off (no public endpoint)

The hand-off is internal to `POST /api/v1/auth/otp/verify`.

- The verify view forwards the `visitor_id` cookie value to the accounts service.
- Inside the existing `transaction.atomic()` block, the recommendations interface folds
  the device profile into the account:
  - account profile absent → copy the device position and uncertainty to the account;
  - account profile present → keep the account profile;
  - tombstone the device profile with `merged_into` set to the account.
- The verify response body is unchanged. No client call is introduced (FR-018).

## 5. Sign-out (modified behaviour, no new endpoint)

The existing logout endpoint additionally clears the device profile:

- delete/clear the device profile for the `visitor_id` cookie;
- clear the `visitor_id` cookie;
- keep the account profile untouched.

## 6. Sort option contract (frontend)

| Surface | Options | Default |
|---|---|---|
| Main catalog | related, cheapest, most expensive | related |
| Company catalog | related, cheapest, most expensive | related |
| Search results | cheapest, most expensive | query relevance (no related option) |

The wire value for the related default is `default` (kept for backward compatibility);
the label is localised to «پیشنهاد برای شما».
