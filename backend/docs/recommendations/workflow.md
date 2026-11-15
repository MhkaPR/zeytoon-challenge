# recommendations — Workflow

## 1. Record a signal

`POST /api/v1/recommendations/signals`

```text
validate kind, plan_ids, and query (search impressions require a query)
  → resolve profile:
      authenticated user → user profile
      else visitor_id cookie → visitor profile
      merged visitor → redirect to the account profile
  → check per-viewer per-minute cap
  → load cached plan space
  → keep plan ids present in the space
  → update clusters:
      search_impression → centroid of matching plans
      destination_visit / details_view → each plan
  → save profile position/uncertainty/version
  → append InterestSignal
```

Response:

```json
{"accepted": 2, "ignored": 0, "profile": "visitor"}
```

## 2. Rank plans

Called by the catalog for the default sort:

```text
RankingService.rank(records, candidate_ids, visitor_id, user)
  → load plan-space bundle
  → map candidate ids to space rows
  → resolve profile (user first, then visitor)
  → InterestClusters.from_profile(profile, bundle)
      matching version → stored clusters
      otherwise       → prior (cold start)
  → compute masked distances
  → order by (distance, newest published_at, id)
```

The deterministic tie-break prevents duplicate or skipped items across pages.

The suggested-plans surface additionally excludes plans with fewer than
`RECOMMENDATION_MIN_RESOURCE_DIMENSIONS` declared CPU/RAM/disk/traffic resources, so
price-only catalogue entries (licenses, domains, add-ons) are not recommended. Repeated
intent explanations are merged into one row and plan lists stay disjoint.

## 3. Merge on login

Called from OTP verification:

```text
StateMerger.merge_on_login(user, visitor_id)
  → lock visitor profile
  → lock/create account profile
  → copy position/uncertainty/version/count/last_signal_at
  → mark visitor.merged_into = user
```

Late signals from the old device are redirected to the account profile.

## 4. Clear on logout

```text
StateMerger.clear_visitor(visitor_id)
  → delete the visitor profile and its signals
```

## 5. Refresh the plan space

```bash
cd backend/src && python manage.py refresh_recommendation_space
```

The command enqueues `refresh_plan_space_task`, which:

```text
load published plan records
  → fit a new space
  → write it under its version key
  → log success/failure
```

Run it from cron (daily by default).

## 6. Rebuild interest clusters

```bash
cd backend/src && python manage.py rebuild_interest_clusters [--dry-run] [--visitor-id UUID] [--user-id ID]
```

Replays each profile's recorded signals into fresh clusters. Useful after changing space
configuration or signal weights.

## 7. Tunables

`conf.py` reads constance values with settings fallbacks:

- `RECOMMENDATION_SIGNAL_WEIGHTS`
- `RECOMMENDATION_UNCERTAINTY`
- `RECOMMENDATION_DRIFT`
- `RECOMMENDATION_NEGATIVE_FACTOR`
- `RECOMMENDATION_PROFILE_TTL_DAYS`
- `RECOMMENDATION_SIGNAL_CAP_PER_MINUTE`
- `RECOMMENDATION_SPACE_CACHE_TTL`
- `RECOMMENDATION_N_BINS`
- `RECOMMENDATION_SEMANTIC_*`
- `RECOMMENDATION_MAX_INTEREST_CLUSTERS`
- `RECOMMENDATION_CLUSTER_DISTANCE_THRESHOLD`
- `RECOMMENDATION_CLUSTER_ACTIVITY_DECAY`
- `RECOMMENDATION_CLUSTER_MIN_ACTIVITY`
- `RECOMMENDATION_CLUSTER_MIN_ACTIVITY_RATIO`
- `RECOMMENDATION_SUGGESTION_CLUSTER_LIMIT`
- `RECOMMENDATION_MIN_RESOURCE_DIMENSIONS`
- `RECOMMENDATION_EXPLAIN_K`
- `RECOMMENDATION_EXPLAIN_MIN_PATTERN_SIZE`
- `RECOMMENDATION_EXPLAIN_ALPHA`
- `RECOMMENDATION_EXPLAIN_MIN_LIFT`
- `RECOMMENDATION_EXPLAIN_MIN_MCC`
- `RECOMMENDATION_EXPLAIN_MIN_CLICKS`
- `RECOMMENDATION_EXPLAIN_NEGATIVE_ENABLED`

## 8. Simulate a viewer

Replay configurable synthetic signals against the real catalog and print the stored
profile, cluster activities, selected plans, and explanations:

```bash
cd backend/src && python manage.py simulate_recommendations \
  --kind destination_visit \
  --plan-type dedicated_server \
  --min-ram 32 \
  --count 20 \
  --keep
```

Useful flags: `--kind` (`destination_visit`, `details_view`, `search_impression`),
`--count`, `--limit`, `--query`, `--plan-type`, `--min-price`, `--max-price`,
`--min-ram`, `--min-cpu`, `--min-disk`, `--top`, `--reset`, `--keep`, and `--json`.
The command uses a fresh visitor UUID by default and hard-deletes the simulated profile
unless `--keep` is passed.

To inspect an existing viewer instead of a throwaway UUID, pass exactly one of
`--visitor-id`, `--user-id`, or `--phone-number`. Existing profiles are never reset
unless `--reset` is supplied:

```bash
cd backend/src && python manage.py simulate_recommendations \
  --phone-number 09046993150 \
  --plan-type dedicated_server \
  --count 5 \
  --top 20 \
  --json
```

## 9. Scenario test report

The presentation-ready matrix of verified and limited behaviours lives in
[`specs/008-intent-pattern-explanations/recommendation-scenarios-report.md`](../../../specs/008-intent-pattern-explanations/recommendation-scenarios-report.md).
It is backed by `backend/src/apps/recommendations/tests/test_recommendation_scenarios.py`.

Two generated, self-contained proof artifacts are written to
`specs/008-intent-pattern-explanations/artifacts/`:

- `recommendation-proof.html` / `.json` — isolated synthetic catalog, every
  scenario runs on a throwaway in-memory SQLite database.
- `recommendation-proof-real-catalog.html` / `.json` — read-only run against the
  real published catalog. It writes no plans, profiles, signals, or spaces and
  includes the statistical gate diagnostics for every intent pattern.

Regenerate both from the repository root:

```bash
.venv/bin/python backend/scripts/generate_recommendation_proof.py
.venv/bin/python backend/scripts/generate_real_catalog_proof.py
```
