# Quickstart Validation: Recommendation Explanations

Runnable checks that prove the feature works end-to-end. See
[contracts/explanations.md](./contracts/explanations.md) for the payload and
[data-model.md](./data-model.md) for entity rules.

## Prerequisites

- Backend deps installed: `uv sync`
- Migrations applied (test DB handles this automatically): `uv run python backend/src/manage.py migrate`
- Frontend deps installed: `cd frontend && yarn install`

## 1. Backend behaviour tests

Run the new suite (added during implementation at
`backend/src/apps/recommendations/tests/test_explanations.py`):

```bash
uv run pytest backend/src/apps/recommendations/tests/test_explanations.py -q
```

Covered behaviours (each maps to spec acceptance scenarios):

- One interest → exactly one explanation for the closest plan (US1/SC-001).
- Several interests → one explanation per retained cluster, bounded by the cluster cap
  (US1/SC-002).
- Textual-closest → sentence describes a product category, no numbers (US2/FR-007).
- Technical-closest → numeric attribute quoted as a real-unit range (US2/FR-008).
- At most the configured number of named features (FR-009).
- Determinism: two calls with unchanged state are byte-identical (FR-013/SC-005).
- Cold-start viewer → empty explanations and unchanged ranking order (FR-011/SC-004).
- Outdated profile → request succeeds, no explanation (FR-015/SC-006).
- Missing attribute → omitted, not zeroed (FR-014).
- Persistence: space and explanations survive a flushed cache (FR-019–FR-022, SC-008/SC-009).

Run the broader recommendation + catalog suites to confirm no regressions:

```bash
uv run pytest backend/src/apps/recommendations backend/src/apps/catalog -q
```

## 2. Endpoint smoke test

With the dev server running (`cd backend/src && python manage.py runserver`), fetch the
endpoint for a fresh visitor and confirm a safe empty result:

```bash
curl -s 'http://localhost:8000/api/v1/recommendations/explanations' \
  -H 'X-Visitor-Id: 00000000-0000-0000-0000-000000000000'
```

Expected: `200` with `{"data": {"explanations": []}}`.

Then record a signal and re-fetch:

```bash
curl -s -X POST 'http://localhost:8000/api/v1/recommendations/signals' \
  -H 'Content-Type: application/json' \
  -H 'X-Visitor-Id: 00000000-0000-0000-0000-000000000000' \
  -d '{"kind":"details_view","plan_ids":[<id>]}'
curl -s 'http://localhost:8000/api/v1/recommendations/explanations' \
  -H 'X-Visitor-Id: 00000000-0000-0000-0000-000000000000'
```

Expected: one explanation whose `matches[].kind` names only `textual` /
`technical_numeric` / `technical_categorical`, with real-unit ranges for numeric matches.

## 2b. Persistence / cache-eviction check

Prove the space and explanations come from PostgreSQL, not Redis:

```bash
# Flush the recommendation cache, then re-fetch the same visitor.
uv run python backend/src/manage.py shell -c "from django.core.cache import cache; cache.clear()"
curl -s 'http://localhost:8000/api/v1/recommendations/explanations' \
  -H 'X-Visitor-Id: 00000000-0000-0000-0000-000000000000'
```

Expected:

- Inspect the tables: `RecommendationSpace` has one active row with a `version`; a
  `RecommendationExplanation` row exists for the visitor with a matching `space_version`.
- The endpoint still returns the same explanations after the cache flush.
- Force a refresh, confirm a new `RecommendationSpace` version becomes active and stale
  explanation rows are recomputed rather than served.

## 3. Frontend rendering

```bash
cd frontend && yarn test explanations
```

Covers: the localized sentence is built from `matches`, textual vs technical phrasing
differs, ranges render with units in Persian, and no raw numbers/scores appear.

## 4. Manual end-to-end

`cd frontend && yarn dev`, open the home page, and interact with several plans of one theme.
Reload and confirm the "پیشنهاد برای شما" strip shows the closest plan with one reason
sentence that names a real attribute range (or a product category for title matches).

## Expected outcomes

- 100% of loads succeed with an explanation for viewers who have real interest.
- Cold-start and outdated-profile viewers see no explanation and the previous order.
- Identical state produces identical text (SC-005).
