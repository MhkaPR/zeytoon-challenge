# Quickstart Validation: Personalized Related Plans Ordering

A runnable guide to prove the feature works end-to-end. It references [spec.md](./spec.md), [plan.md](./plan.md), [data-model.md](./data-model.md), and [contracts/recommendations-api.md](./contracts/recommendations-api.md) instead of duplicating their details.

## Prerequisites

- Python 3.14 with the project virtualenv; backend dependencies installed (`uv sync`).
- PostgreSQL (or the local default) and Redis reachable; `REDIS_URL` set.
- The frontend dependencies installed (`cd frontend && yarn install`).
- At least three published plans of one type and one of another type, so ranking is observable. Use the ops publish flow or seed rows directly.

## Setup

```bash
# from repo root
uv sync
cd backend/src && python manage.py migrate && python manage.py runserver 0.0.0.0:8000

# in a second terminal
cd frontend && yarn dev
```

Open `http://localhost:3000`. The catalogue fetches through the same-origin `/api/*` proxy, so the visitor cookie is first-party.

## Scenario 1 - Cold start is deterministic

1. Open the home page in a fresh private window.
2. Note that the sort control shows the related option first, and the order.
3. Open the same URL in a second fresh private window.

Expected: both windows show the same relative order, and the related option is selected by default (SC-001, SC-009, FR-020).

## Scenario 2 - Signals move the order (anonymous)

1. In one window, open details for several plans of the less-favoured type, then open the destination page of one of them.
2. Reload the catalogue.

Expected: plans of that type rank higher than in Scenario 1, and the destination-page action produced a larger shift than a details view alone (SC-002, FR-004, FR-005).

Verify identity resolution at the API level:

```bash
# visitor cookie value copied from the browser devtools
curl -X POST http://localhost:8000/api/v1/recommendations/signals \
  -H 'Content-Type: application/json' \
  -H 'Cookie: visitor_id=<uuid>' \
  -d '{"kind":"details_view","plan_ids":[<id>]}'
```

Expected: `{"data": {"accepted": 1, "ignored": 0, "profile": "visitor"}}`.

## Scenario 3 - Search keeps relevance and emits one impression

1. Type a query that matches several plans and submit.
2. Observe the result order.
3. On the exact same query, confirm the sort control offers only cheapest and most expensive.

Expected: results stay in query-relevance order and the related option is absent (SC-006, FR-015). Check the backend logs to confirm one `search_impression` signal was recorded for the first page only.

## Scenario 4 - Sign-in hand-off

1. With anonymous signals recorded, sign in using a fresh phone number.
2. Confirm the catalogue order continues without a jump.
3. Sign out, reload, and confirm the order is back to the cold-start order.
4. Sign in again with the same account and confirm the account order returns.

Expected: the account adopted the device history on first sign-in, sign-out cleared the device, and the account history survived (SC-004, SC-005, FR-008, FR-009, FR-010).

Verify in the Django shell:

```bash
python manage.py shell -c "
from apps.recommendations.models import InterestProfile
print(list(InterestProfile.objects.values('user_id','visitor_id','signal_count','merged_into_id')))
"
```

Expected: one tombstoned visitor profile with `merged_into_id` set, and one active account profile.

## Scenario 5 - Existing sorts are unchanged

1. Choose cheapest; confirm strictly ascending prices.
2. Choose most expensive; confirm descending prices.
3. Return to related; confirm the personalised order is restored.

Expected: SC-008, FR-014.

## Scenario 6 - Pagination does not repeat

1. With the related sort, page through the catalogue without interacting.
2. Collect plan ids from each page.

Expected: no duplicate ids across consecutive pages while no new signal is recorded (SC-007, FR-013).

## Scenario 7 - Undeclared attributes are not penalized

1. Ensure the corpus contains a plan type that lacks some numeric attributes (for example a CDN plan).
2. Record interest in plans of a type that declares those attributes, then reload the catalogue across all types.

Expected: the CDN plan is not pushed to the bottom merely for lacking attributes it does not declare (FR-016).

## Automated checks

```bash
# backend
uv run pytest backend/src/apps/recommendations/tests backend/src/apps/catalog/tests backend/src/apps/accounts/tests -q

# frontend
cd frontend && yarn test && yarn lint && yarn build
```

Expected: all suites pass and the frontend build succeeds.

## Rollback / disable

- Change the frontend sort options prop to drop the related default; the backend keeps `sort=default` meaningful, so no data migration is required.
- The two new models are additive; reverting the app's migration has no impact on catalogue records.
