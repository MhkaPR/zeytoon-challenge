# Implementation Plan: Periodic PCA Space Expansion

**Branch**: `006-pca-space-expansion` | **Date**: 2026-11-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-pca-space-expansion/spec.md`

## Summary

Extend the feature-005 recommendation space with ten semantic dimensions derived from
published plan titles using the `pca.py` algorithm family (character n-gram hashing +
principal component analysis). Recalculate the semantic components on a configurable
schedule through a Django Task enqueued by a management command, and publish the new
space to Redis through an atomic active-pointer swap so catalogue reads always see one
complete space. Viewer preference states automatically cover the new dimensions and
outdated profiles fall back to the cold-start prior without failing.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Django 6.1, Django REST Framework, numpy 2.5 (existing),
`scikit-learn` (new, for `HashingVectorizer` + `PCA`), django-tasks-db, django-constance,
django-redis

**Storage**: PostgreSQL (source of truth for published plans and interest profiles);
Redis (cached plan-space bundle and refresh lock)

**Testing**: pytest + pytest-django (`uv run pytest`), locmem cache in tests

**Target Platform**: Linux server (WSGI, Docker production image)

**Project Type**: Web service — Django modular monolith with a Next.js frontend

**Performance Goals**: Sustain the existing 100 RPS read profile; semantic refresh runs
off the request path in a database worker; catalogue reads hit the cached bundle

**Constraints**: No public API contract changes; atomic space swap; no catalogue request
blocked by a recalculation; no new persisted models or migrations; all tunables
constance/settings-backed

**Scale/Scope**: Demo-scale catalogue (tens to low hundreds of published plans); ten
semantic dimensions by default

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Product Domain | Recommendations improve plan comparison/search ordering | PASS |
| II. Cost and External Resources | No LLM or external paid service added | PASS |
| III. Security and Secrets | No new secret; titles are public plan data | PASS |
| IV. Data Governance | Redis and all services remain self-hosted | PASS |
| V. Architecture | Semantic space stays inside `apps.recommendations`; catalogue and task read plans through `CatalogInterface`; no cross-module table access | PASS |
| VI. Performance and Scalability | Refresh is asynchronous; cached reads preserved; only ten extra dimensions on the hot path | PASS |
| VII. Observability | Structured JSON logs for refresh start/success/failure and skipped runs | PASS |
| VIII. Quality and Testing | Each new behaviour ships with automated tests | PASS |
| IX. Data Retention | No change to profile/signal retention | PASS |
| X. Crawling Ethics | No crawling change | PASS |
| XI. Authentication | No auth change | PASS |
| XII. Prefer Established Libraries | Use scikit-learn `HashingVectorizer`/`PCA` instead of hand-rolled text hashing and SVD | PASS |
| XIII. Configurable Values | Semantic dimension count, n-gram range, hash size, refresh interval, lock TTL in constance/settings | PASS |

**Gate result**: PASS. No violations require justification.

## Project Structure

### Documentation (this feature)

```text
specs/006-pca-space-expansion/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── space-cache.md
├── checklists/
│   └── requirements.md
└── tasks.md              # created by $speckit-tasks
```

### Source Code (repository root)

```text
backend/src/apps/recommendations/
├── conf.py                                      # MODIFIED: semantic + refresh tunables
├── tasks.py                                     # NEW: refresh_plan_space_task
├── management/commands/
│   └── refresh_recommendation_space.py          # NEW: due-check + enqueue
├── services/v1/
│   ├── semantic.py                              # NEW: SemanticEncoder (hash + PCA)
│   ├── features.py                              # MODIFIED: map plan title
│   ├── space.py                                 # MODIFIED: append 10 semantic dims
│   ├── store.py                                 # MODIFIED: atomic active-pointer swap
│   ├── ranking.py                               # MODIFIED: reconcile outdated profiles
│   └── signals.py                               # MODIFIED: reconcile outdated profiles
└── tests/
    ├── test_semantic.py                         # NEW
    ├── test_space.py                            # MODIFIED
    ├── test_store.py                            # NEW
    ├── test_tasks.py                            # NEW
    └── test_ranking.py                          # MODIFIED

backend/src/config/settings/base.py              # MODIFIED: constance defaults
pyproject.toml                                   # MODIFIED: scikit-learn dependency
```

**Structure Decision**: The feature is confined to the existing
`apps.recommendations` module. The semantic encoder is a service beside the existing
space/state services; the periodic entry point follows the established
`apps.pipeline` pattern of a `@task` body plus a management command that enqueues due
work. No frontend change and no new app are required.

## Complexity Tracking

| Item | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| New `scikit-learn` dependency | Provides the exact `HashingVectorizer` + `PCA` implementation prototyped in `pca.py` and satisfies Principle XII | A hand-rolled numpy SVD and hashing implementation would duplicate a mature library and violate Principle XII |
| Active-pointer cache indirection | Guarantees atomic swap and last-known-good fallback (FR-006, FR-013) | Writing only the versioned key would let a failed refresh be bypassed by on-demand fitting and would not preserve the previous space |

## Post-Design Constitution Re-check

The Phase 1 design keeps the Phase 0 result. The semantic encoder and expanded space stay
inside `apps.recommendations`; the refresh task reads plans through `CatalogInterface`;
all tunables live in constance/settings; no new persisted model, migration, external
service, or credential is introduced. The only hot-path change is ten additional
dimensions in the existing vector operations, which stays within the 100 RPS target. No
new gate violations.
