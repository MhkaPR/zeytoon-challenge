# Quickstart Validation: Intent-Pattern Recommendation Explanations

## Prerequisites

- Python 3.14 environment with `uv sync` completed.
- PostgreSQL and Redis available for the backend test/run environment.
- Frontend dependencies installed with `cd frontend && yarn install`.

## Backend validation

Run the focused suites:

```bash
cd /home/mhkapr/Documents/personal/projects/torob-challenge
.venv/bin/python -m pytest backend/src/apps/recommendations/tests/test_intent_patterns.py -q
.venv/bin/python -m pytest backend/src/apps/recommendations/tests/test_intent_scoring.py -q
.venv/bin/python -m pytest backend/src/apps/recommendations/tests/test_explanation.py -q
.venv/bin/python -m pytest backend/src/apps/recommendations/tests/test_ranking.py -q
```

Run the regression suites:

```bash
.venv/bin/python -m pytest backend/src/apps/recommendations/tests -q
.venv/bin/python -m pytest backend/src/apps/catalog/tests/test_related_sort.py -q
```

Expected outcomes:

- Registry tests confirm exactly `{cheap, value, spec_heavy, premium, exploring}` and no
  `text_specific`.
- Scoring tests confirm Gate 1, Gate 2, Gate 3, MCC sign, and `exploring` exclusion.
- Explanation tests confirm winner selection, corroboration rejection, and the
  `exploring` fallback.
- Primary-intent tests confirm occurrence counting, tie-breaking, and that `exploring`
  never wins over a real intent.
- Existing feature-005 and feature-006 tests still pass.

## API validation

With a seeded viewer and catalog, request:

```bash
curl -s -H "X-Visitor-Id: <uuid>" \
  http://localhost:8000/api/v1/catalog/plans/suggested | jq
```

Confirm:

- `data` contains the suggested plans.
- `explanations` has one entry per cluster.
- `primary_explanation` is present and contains `occurrence_count` and `cluster_count`.
- No message contains a numeric range.
- A cold-start viewer receives `intent: "exploring"` and `confidence: null`.

Confirm the removed endpoint no longer responds:

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  http://localhost:8000/api/v1/recommendations/explanations
```

Expected: `404`.

## Frontend validation

```bash
cd frontend
yarn test explanations
yarn build
```

Expected outcomes:

- The suggested-plans surface renders exactly one primary intent message.
- No per-cluster messages or numeric attribute ranges are rendered.
- The production build succeeds with no TypeScript or ESLint errors.

## Determinism check

Request the suggested endpoint twice with the same visitor id and unchanged catalog:

```bash
curl -s -H "X-Visitor-Id: <uuid>" \
  http://localhost:8000/api/v1/catalog/plans/suggested > /tmp/first.json
curl -s -H "X-Visitor-Id: <uuid>" \
  http://localhost:8000/api/v1/catalog/plans/suggested > /tmp/second.json
diff /tmp/first.json /tmp/second.json
```

Expected: no differences.

## Configuration check

Change `RECOMMENDATION_EXPLAIN_MIN_LIFT` through django-constance and confirm the next
request applies the new threshold without a redeploy. Restore the default afterward.
