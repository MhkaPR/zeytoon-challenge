# Implementation Plan: Periodic PCA Space Expansion

**Branch**: `006-pca-space-expansion` | **Date**: 2026-11-07 | **Spec**: [spec.md](./spec.md)

## Summary

Add a small semantic encoder that turns plan titles into ten values using the `pca.py`
algorithm (`HashingVectorizer` + `PCA`). Append those ten values to the existing plan
space, refresh the cached space with a scheduled Django Task, and replace the single
preference vector with a bounded set of interest clusters so several themes (python,
node, email) stay represented. No new models, no public API change.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Django 6.1, numpy 2.5, `scikit-learn` (new), django-tasks-db,
django-constance, django-redis

**Storage**: PostgreSQL (plans, profiles); Redis (cached space)

**Testing**: pytest + pytest-django

**Project Type**: Django web service

**Constraints**: No new models or migrations; no public API change; refresh off the
request path; bounded multi-interest state; all tunables in constance/settings

**Scale/Scope**: Demo-scale catalogue; ten semantic dimensions

## Constitution Check

| Principle | Result |
|---|---|
| I. Product Domain | PASS — improves plan comparison |
| II. Cost | PASS — no LLM or paid service |
| III. Security | PASS — public titles only |
| IV. Data Governance | PASS — existing self-hosted Redis |
| V. Architecture | PASS — changes stay in `apps.recommendations`; plans read via `CatalogInterface` |
| VI. Performance | PASS — refresh is asynchronous; cached reads preserved |
| VII. Observability | PASS — structured refresh logs |
| VIII. Testing | PASS — tests for each behaviour |
| IX–XI | PASS — no retention, crawling, or auth change |
| XII. Libraries | PASS — scikit-learn instead of hand-rolled PCA |
| XIII. Configurable Values | PASS — dimension count, n-gram range, hash size, seed in constance |

**Gate result**: PASS.

## Project Structure

```text
backend/src/apps/recommendations/
├── conf.py                                  # MODIFIED: semantic tunables
├── tasks.py                                 # NEW: refresh_plan_space_task
├── management/commands/
│   └── refresh_recommendation_space.py      # NEW: enqueue refresh
├── services/v1/
│   ├── semantic.py                          # NEW: title -> 10 PCA values
│   ├── features.py                          # MODIFIED: include plan title
│   ├── space.py                             # MODIFIED: append semantic dimensions
│   ├── store.py                             # MODIFIED: force-refresh helper
│   ├── state.py                             # MODIFIED: InterestClusters
│   ├── ranking.py                           # MODIFIED: min distance across clusters
│   └── signals.py                           # MODIFIED: update nearest cluster
├── management/commands/
│   ├── refresh_recommendation_space.py      # existing
│   └── rebuild_interest_clusters.py         # NEW: replay historical signals
└── tests/
    ├── test_semantic.py                     # NEW
    ├── test_space.py                        # MODIFIED
    ├── test_tasks.py                        # NEW
    ├── test_state.py                        # MODIFIED: cluster tests
    └── test_ranking.py                      # MODIFIED: multi-theme ranking

backend/src/config/settings/base.py          # MODIFIED: constance defaults
backend/src/apps/catalog/views/v1/catalog.py # MODIFIED: visitor cookie fallback
frontend/src/features/home/PlanCatalog.tsx   # MODIFIED: forward visitor id on paging
frontend/src/features/home/MainBody.tsx      # MODIFIED: pass visitor id
frontend/app/page.tsx                        # MODIFIED: pass visitor id
frontend/app/companies/[domain]/page.tsx     # MODIFIED: pass visitor id
frontend/app/search/page.tsx                 # MODIFIED: pass visitor id
pyproject.toml                               # MODIFIED: scikit-learn
```

**Structure Decision**: Everything stays in the existing recommendations app.
`InterestProfile.position` and `.uncertainty` become lists of cluster vectors; a flat
legacy list is read as one cluster. Ranking takes the minimum distance across clusters.
Pagination forwards the visitor id from the server render so client-side page changes
stay personalized, and a maintenance command replays historical signals to rebuild
clusters after the state format changes.

## Complexity Tracking

| Item | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| `scikit-learn` dependency | Matches `pca.py` and Principle XII | Hand-rolled PCA duplicates a mature library |
| Bounded interest clusters | A single vector averages python, node, and email into one point and swings to the latest theme | Decay or per-query caps still leave one averaged interest and cannot represent three themes at once |
