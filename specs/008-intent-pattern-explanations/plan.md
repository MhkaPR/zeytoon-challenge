# Implementation Plan: Intent-Pattern Recommendation Explanations

**Branch**: `008-intent-pattern-explanations` | **Date**: 2026-11-10 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-intent-pattern-explanations/spec.md`

## Summary

Replace the feature-attribution explanation layer with intent-pattern detection. For each
interest cluster, build the same top-K nearest candidate set used by suggested plans,
score four pre-declared real intent patterns with Fisher Exact, Lift, and MCC gates, and
corroborate the winner against the viewer's outbound clicks. Return every cluster's intent
explanation and render one UI row per cluster, including repeated intents. Remove the
separate explanation endpoint, the feature-reason serializers/services, and the persisted
explanation model. No new persisted model or migration is introduced.

## Technical Context

**Language/Version**: Python 3.14 (Django backend); TypeScript with React 19 and Next.js App Router (frontend)

**Primary Dependencies**: Django 6.1, Django REST Framework, NumPy, SciPy (`scipy.stats.fisher_exact`), scikit-learn (existing), django-constance, next-intl, HeroUI

**Storage**: PostgreSQL is the source of truth for the recommendation space and interest profiles; Redis is a read-through cache. No new persisted explanation model or table.

**Testing**: pytest + pytest-django for backend; Vitest + Testing Library for frontend

**Target Platform**: Linux server (Django/DRF) and modern web browsers (Next.js)

**Project Type**: Web application (Django backend + Next.js frontend)

**Performance Goals**: Preserve the 100 RPS read-heavy target. Pattern membership is computed once per request in vectorized form; each request performs at most four Fisher tests per cluster (maximum four clusters) and adds one signal-history query.

**Constraints**: No new migrations; deterministic output for the same profile and space version; per-cluster evaluation only; maximum four interest clusters; candidate set size defaults to 20; no attribute ranges in output; no Persian strings in backend service code; messages and the negative-intent flag are constance-backed.

**Scale/Scope**: Four real intent patterns plus one fallback, up to four clusters, catalog sizes in the hundreds to low thousands, and one suggested-plans response per page load.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Product Domain | PASS | Explains recommended plans in a search/comparison product. |
| II. Cost and External Resources | PASS | No LLM or paid external service is introduced. |
| III. Security and Secrets | PASS | No secrets or credentials are touched. |
| IV. Data Governance | PASS | Uses existing Iran-hosted PostgreSQL and Redis only. |
| V. Architecture | PASS | Catalog calls the recommendations interface; no cross-module table access. |
| VI. Performance and Scalability | PASS | Bounded O(N) pattern masks plus at most 16 Fisher tests per request; one extra signal query. |
| VII. Observability | PASS | No new hot-path logging; existing structured logging remains. |
| VIII. Quality and Testing | PASS | Unit tests cover registry, gates, corroboration, fallback, aggregation, and determinism; regression suites remain. |
| IX. Data Retention | PASS | No new stored personal data; existing profile/signal retention applies. |
| X. Crawling Ethics | PASS | No crawler changes. |
| XI. Authentication | PASS | No auth changes. |
| XII. Established Libraries | PASS | Fisher Exact uses SciPy; MCC uses the canonical guarded formula because no maintained count-based helper avoids materializing full arrays. |
| XIII. Configurable Values | PASS | All six thresholds/sizes are django-constance runtime constants with defaults. |

**Post-design re-check**: PASS. The design adds no persistence, no cross-module table
access, no hard-coded thresholds, and no unbounded per-request work.

## Project Structure

### Documentation (this feature)

```text
specs/008-intent-pattern-explanations/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── suggested-plans.md
├── checklists/
│   └── requirements.md
└── spec.md
```

### Source Code (repository root)

```text
backend/src/apps/recommendations/
├── conf.py                                  # replace obsolete feature-explanation tunables
├── interfaces.py                            # expose suggest_with_explanations
├── models/
│   └── __init__.py                          # no explanation model re-export
├── serializers/v1/
│   ├── intent_explanations.py               # NEW: per-cluster serializers
│   └── reasons.py                           # DELETE
├── services/v1/
│   ├── intent_patterns.py                   # NEW: registry, predicates, messages
│   ├── intent_scoring.py                    # NEW: contingency table, gates, MCC, Lift
│   ├── explanation.py                       # NEW: per-cluster orchestration
│   ├── ranking.py                           # call explanation from suggest
│   └── reasons.py                           # DELETE
└── tests/
    ├── test_intent_patterns.py              # NEW
    ├── test_intent_scoring.py               # NEW
    ├── test_explanation.py                  # NEW
    ├── test_explanations.py                 # DELETE/REPLACE
    └── test_ranking.py                      # MODIFIED

backend/src/apps/catalog/
├── views/v1/catalog.py                      # suggested response includes primary explanation
└── tests/test_related_sort.py               # regression coverage

backend/src/config/settings/base.py          # constance keys for the six intent tunables

frontend/src/lib/api/
├── intentExplanations.ts                    # NEW: typed intent explanation contract
└── publicCatalog.ts                         # parse primary explanation

frontend/src/features/home/
├── SuggestedPlans.tsx                       # render one row per cluster explanation
├── planCatalog/PlanRow.tsx                  # hidden-scrollbar row with prev/next controls
├── explanationText.ts                       # DELETE
└── planCatalog/WhyRecommended.tsx           # DELETE or replace with primary badge

frontend/src/lib/i18n/messages/fa.json       # remove obsolete feature-range copy
frontend/tests/explanations.test.tsx         # REPLACE with intent rendering tests
```

**Structure Decision**: Keep the existing modular-monolith layout. Backend behavior lives
in `apps/recommendations/services/v1` behind `RecommendationsInterface`; the catalog view
only serializes the interface result. Frontend consumes the new response shape and renders
the backend-provided primary message. No new app, model, or migration is created.

## Complexity Tracking

No constitution violations. The design deliberately keeps scoring and aggregation in
separate modules so adding a pattern does not require changing the scoring code.
