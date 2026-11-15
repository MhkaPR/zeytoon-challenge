# Recommendation System Test Scenario Report

**Date**: 2026-11-10

**Test file**: `backend/src/apps/recommendations/tests/test_recommendation_scenarios.py`

**Result**: 21 out of 21 scenarios passed. Total related tests: 95 backend tests and 3 frontend tests.

## Generated proof artifacts

Two self-contained artifacts are checked in under `artifacts/`:

- `recommendation-proof.html` / `.json` — 22/22 scenarios on an isolated
  synthetic catalog in a throwaway in-memory database.
- `recommendation-proof-real-catalog.html` / `.json` — 10/10 verified scenarios
  plus 1 documented statistical limit, run **read-only** against the real
  published catalog. The HTML includes per-pattern Fisher/lift/MCC gate
  diagnostics, so a rejected intent is explained rather than hidden.

Regenerate them with:

```bash
.venv/bin/python backend/scripts/generate_recommendation_proof.py
.venv/bin/python backend/scripts/generate_real_catalog_proof.py
```

## What does this report prove?

These scenarios run the real system path: signal registration, profile update,
cluster formation, plan ranking, resource filtering, and intent explanation construction. No assertions
are written on fake internal values; the output is exactly what the API and UI
return.

The test catalog has four completely separate groups:

| Group | Rows | Price | Specs | Role |
| --- | --- | --- | --- | --- |
| `cheap` | 0-29 | Low | Weak | Economy detection |
| `value` | 30-59 | Low/Medium | Strong | Value-for-money detection |
| `overpriced` | 60-89 | High | Weak | Expensive and weak plans; should not become "value" |
| `premium` | 90-119 | High | Strong | Premium detection |

This layout allows the statistical gates to pass **with production default settings** (without loosening
thresholds): pattern size ≥ 30, Fisher p ≤ 0.05, Lift ≥ 2.0, and |MCC| ≥ 0.20.

## Successful Scenarios

| # | Scenario | Expected Behavior | Result |
| --- | --- | --- | --- |
| 1 | Visitor with no history | "Exploring" message + suggested plans | ✅ |
| 2 | Click on premium plans | intent = `premium` and "premium" text | ✅ |
| 3 | Click on cheap plans | intent = `cheap` and "economy" text | ✅ |
| 4 | Click on high-spec, reasonably-priced plans | intent = `value` and "value for money" text | ✅ |
| 5 | Click on expensive and weak plans | Should not become `value`; "exploring" | ✅ |
| 6 | Only search results impression (no outbound click) | Intent detection from `search_impression` | ✅ |
| 7 | Only plan details view | Intent detection from `details_view` | ✅ |
| 8 | Cheap search without click | `cheap` detection from search signal | ✅ |
| 9 | Two separate interests (cheap + premium) | Two independent explanation rows | ✅ |
| 10 | Repeated interest in two clusters | Merge into one `premium` row | ✅ |
| 11 | Row merging | No plan duplicated between rows | ✅ |
| 12 | Plan with no resources (price only) | Excluded from suggestions | ✅ |
| 13 | Plan with one resource (RAM only) | Remains eligible with default setting | ✅ |
| 14 | Change minimum resource dimensions to 2 | Single-resource plan is excluded | ✅ |
| 15 | Old interest + new clicks | Fresh interest dominates (decay) | ✅ |
| 16 | Two independent visitors | Profiles and suggestions do not mix | ✅ |
| 17 | Signal flood | Signal rate limit is enforced | ✅ |
| 18 | Public API `/api/v1/catalog/plans/suggested` | Plans + explanation in one response | ✅ |
| 19 | Invalid visitor ID | Safe fallback to cold start | ✅ |
| 20 | Re-run with same input | Completely identical output (deterministic) | ✅ |
| 21 | `simulate_recommendations` command | Intent report in live demo | ✅ |

## Run Commands

```bash
# 21 presentation scenarios
.venv/bin/python -m pytest \
  backend/src/apps/recommendations/tests/test_recommendation_scenarios.py -q

# Full recommendation space + related sort
.venv/bin/python -m pytest \
  backend/src/apps/recommendations/tests \
  backend/src/apps/catalog/tests/test_related_sort.py -q

# Frontend explanations
cd frontend && yarn test explanations
```

Recorded result: `21 passed`, `95 passed`, and `3 passed`.

## Live Demo with Simulation Command

```bash
cd backend/src

# New visitor, dedicated plans, 5 signals
python manage.py simulate_recommendations \
  --plan-type dedicated_server --count 5 --top 10 --keep

# Real user profile by phone number (without reset)
python manage.py simulate_recommendations \
  --phone-number 09046993150 \
  --plan-type dedicated_server \
  --count 5 --top 20 --json
```

Identification options: `--visitor-id`, `--user-id`, `--phone-number`.
`--reset` clears the profile only when explicitly requested; without it, real data
is only read and reinforced.

## Limitations (Honest)

- Intent detection is **statistical**, not a semantic guesser. If there are insufficient signals or the catalog
  pattern is weak, "exploring" is the correct and expected output.
- Thresholds are configurable in `conf.py`. The above report was run with production defaults;
  the threshold values are shown in the table above.
- An old interest with a few stray clicks is not immediately removed; `RECOMMENDATION_CLUSTER_ACTIVITY_DECAY`
  and the cluster activity ratio determine when an old cluster is removed from suggestions.
- When two clusters resolve to the same intent, the API merges them into one row and
  renumbers `cluster_id` from zero, so the response never exposes a gap such as `0` and `2`.
- Plans that declare no resources (domain, license, add-on) are deliberately excluded from the
  suggestion level; even if they have a price.
- If a real profile still shows "exploring", first use the `--phone-number ... --json` command
  to see whether signals have reached the profile at all and whether `signal_count` and
  `activities` have grown.

## Summary for Presentation

The system works in proven main paths: cold start, detection of four intents,
non-click signals, multiple interests, duplicate merging, resource filtering, decay, profile isolation,
rate limiting, API, and deterministic behavior. The weak point is scarce or ambiguous data, whose output
is intentionally "exploring" and is separated from real errors by the above tests.
