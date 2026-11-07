# Implementation Plan: Periodic PCA Space Expansion

**Branch**: `006-pca-space-expansion` | **Date**: 2026-11-07 | **Spec**: [spec.md](./spec.md)

## Summary

Add a small semantic encoder that turns plan titles into ten values using the `pca.py`
algorithm (`HashingVectorizer` + `PCA`). Append those ten values to the existing plan
space, refresh the cached space with a scheduled Django Task, and let the existing
profile reconciliation handle dimension changes. No new models, no public API change.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Django 6.1, numpy 2.5, `scikit-learn` (new), django-tasks-db,
django-constance, django-redis

**Storage**: PostgreSQL (plans, profiles); Redis (cached space)

**Testing**: pytest + pytest-django

**Project Type**: Django web service

**Constraints**: No new models or migrations; no public API change; refresh off the
request path; all tunables in constance/settings

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
│   └── store.py                             # MODIFIED: force-refresh helper
└── tests/
    ├── test_semantic.py                     # NEW
    ├── test_space.py                        # MODIFIED
    └── test_tasks.py                        # NEW

backend/src/config/settings/base.py          # MODIFIED: constance defaults
pyproject.toml                               # MODIFIED: scikit-learn
```

**Structure Decision**: Everything stays in the existing recommendations app. Ranking
and signal services need no change because they already rebuild state when the version
or dimension count differs.

## Complexity Tracking

| Item | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| `scikit-learn` dependency | Matches `pca.py` and Principle XII | Hand-rolled PCA duplicates a mature library |
