# Implementation Plan: Recommendation Explanations

**Branch**: `007-recommendation-explanations` | **Date**: 2026-11-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-recommendation-explanations/spec.md`

## Summary

For each interest cluster a viewer holds, find the closest plan in the recommendation
space and produce one short, human-readable reason for it. Dimensions are split into two
categories — textual/lexical (the ten title-derived semantic dimensions, scored as one
group) and technical specifications (scored individually) — and the closest three feature
groups are named. Technical features are reverted from their `[0, 1]` normalized value back
into the catalogue's real unit and quoted as a small range; a textual match is described as
interest in a product category. The backend computes structured explanations on read (no
recomputation when already stored) and exposes them through a read-only endpoint under the
recommendations module; the frontend renders the localized sentence from the existing i18n
catalogue. No existing ranking, sorting, or signal API changes.

To make this durable, the recommendation space and the explanation results are persisted in
PostgreSQL (new models in the `recommendations` module), with Redis used only as a
read-through cache that can be evicted safely. This replaces the current cache-only
`PlanSpaceProvider` storage without changing its public read contract.

This supersedes feature 006's assumption that "the existing cache is reused; no new
datastore is introduced": the space it introduced is now database-backed. Feature 006's
ranking behaviour and its read contract are unchanged.

## Technical Context

**Language/Version**: Python 3.14 (backend), TypeScript / Next.js (frontend)

**Primary Dependencies**: Django 6 + Django REST Framework, numpy, scikit-learn (existing
semantic encoder), django-constance (runtime tunables), drf-spectacular (API docs);
frontend uses next-intl for localized copy.

**Storage**: PostgreSQL is the source of truth for all recommendation state. The fitted
plan space (vectors, dimension names, value scales, version) and the computed explanation
results are **persisted as database models**; Redis becomes an optional read-through cache in
front of them, not the primary store. This adds models and a migration to the
`recommendations` module and a cache-invalidation step on space refresh.

**Testing**: pytest + pytest-django for backend behaviour tests under
`backend/src/apps/recommendations/tests/`; Vitest + Testing Library for the frontend
rendering under `frontend/tests/`.

**Target Platform**: Linux server (Docker-composed web service); browser client.

**Project Type**: Web application (Django/DRF backend + Next.js frontend).

**Performance Goals**: Explanations add no request-visible latency beyond the existing
ranked read; they reuse the already-loaded plan-space bundle and cached profile. Must hold
the platform target of 100 RPS read-heavy traffic.

**Constraints**: The `PlanSpace` bundle (values, masks, binners, categorical vocabularies)
and explanation results MUST survive restarts and cache eviction, so they are read from
PostgreSQL when the cache is cold. Output MUST be deterministic for identical state. All
tunables (feature count, range width) MUST be configurable (Constitution XIII).

**Scale/Scope**: Up to the configured maximum interest clusters per viewer (default four),
one closest plan per cluster, at most three named features per explanation.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment |
|-----------|------------|
| I. Product Domain | Pass — explains search/comparison recommendations; in-domain. |
| II. Cost / External Resources | Pass — no LLM use; purely local computation. |
| III. Security & Secrets | Pass — reads only existing public plan attributes and the viewer's own profile; no new secrets. |
| IV. Data Governance | Pass — persistence uses the existing Iran-hosted PostgreSQL; Redis stays local cache. |
| V. Architecture | Pass — new models live in the `recommendations` module behind `RecommendationsInterface`; other modules do not touch its tables. |
| VI. Performance & Scalability | Pass — persisted space is read once per request and cached in Redis (read-through), bounded by cluster count; no N-per-plan work. |
| VII. Observability | Pass — structured logging on explanation generation, sampled to avoid loop noise. |
| VIII. Quality & Testing | Pass — behaviour tests for each category, revert, and cap rule (see data model / quickstart). |
| IX. Data Retention | Pass — space rows are versioned (one active, old versions prunable); explanation rows follow the existing 180-day profile retention. |
| X. Crawling Ethics | N/A — no crawling. |
| XI. Authentication | Pass — read endpoint honours existing anonymous/authenticated identity; no new auth path. |
| XII. Established Libraries | Pass — reuses numpy/DRF/next-intl; no hand-rolled replacement of covered capability. |
| XIII. Configurable Values | Pass — feature count and range width are constance/settings-backed (`RECOMMENDATION_*`). |

No violations; Complexity Tracking is not required.

## Project Structure

### Documentation (this feature)

```text
specs/007-recommendation-explanations/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── explanations.md
└── tasks.md             # Phase 2 output ($speckit-tasks — not created here)
```

### Source Code (repository root)

```text
backend/src/
├── config/settings/base.py                     # add explanation tunables to CONSTANCE_CONFIG
└── apps/recommendations/
    ├── conf.py                                 # explanation config accessors
    ├── interfaces.py                           # expose explanation call on RecommendationsInterface
    ├── serializers/v1/explanations.py          # response serializer
    ├── services/v1/
    │   ├── features.py                         # (existing) plan feature mapping
    │   ├── space.py                            # (existing) dimension names + value scales
    │   ├── state.py                            # (existing) clusters / nearest
    │   ├── ranking.py                          # (existing) ranking facade
    │   └── explanations.py                     # NEW: closest-plan + feature explanation service
    ├── models/
    │   ├── recommendation_space.py             # NEW: persisted space (vectors, names, scales, version)
    │   ├── recommendation_explanation.py       # NEW: persisted per-viewer explanation result
    │   └── __init__.py                         # re-export new models
    ├── migrations/                             # NEW migration for the two models
    ├── views/v1/explanations.py                # NEW: read-only endpoint
    ├── urls.py                                 # register the new route
    └── tests/                                  # add test_explanations.py

frontend/
├── src/lib/api/explanations.ts                 # NEW: typed fetch for explanations
├── src/features/home/SuggestedPlans.tsx        # render the reason on the closest card
├── src/features/home/planCatalog/PlanCard.tsx  # optional reason slot
├── src/lib/i18n/messages/fa.json               # explanation sentence templates
└── tests/explanations.test.tsx                 # NEW: rendering + determinism test
```

**Structure Decision**: Web application. Backend work is confined to the existing
`recommendations` module (services → interface → versioned serializer/view → route), and
frontend work is confined to the existing feature module for suggested plans plus the i18n
catalogue. No new module, model, or datastore is added.

## Complexity Tracking

No constitution violations; not applicable.
