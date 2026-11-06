# Implementation Plan: Personalized Related Plans Ordering

**Branch**: `005-related-plans-sort` | **Date**: 2026-11-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/005-related-plans-sort/spec.md`

**Note**: This plan was produced by `$speckit-plan`. The design follows
`backend-rules.md`, `frontend-rules.md`, and `.specify/memory/constitution.md`.

## Summary

The catalog gains a "related plans" sort option that is the default on the main and
company catalogs. Ordering is driven by a per-viewer preference model: an anonymous,
device-scoped profile for signed-out visitors, and an account-scoped profile for
signed-in visitors. Three interaction signals feed the model — visiting a plan's
destination page (strongest), opening plan details (moderate), and the first page of
results for a typed search (weakest). Signals are the only client-initiated
recommendation action. On sign-in, the platform folds the device profile into the
account (account history wins when both exist); on sign-out, the device profile is
cleared and the account profile is retained.

Technically this is delivered as a new Django application,
`apps.recommendations`, that owns the preference model, the signal recorder, the merge
logic, and a ranking facade. `apps.catalog` reaches it only through a declared
interface. The backend keeps a fitted plan space in Redis, exposes one client-facing
signal endpoint, and ranks the entire filtered catalogue before paginating. The
frontend adds a visitor cookie via Next middleware, forwards the visitor identity on
server-side catalogue fetches, emits signals from the plan card, and hides the related
option on the search results page.

## Technical Context

**Language/Version**: Python 3.14 (backend); TypeScript 5 + React 19.3 (frontend)

**Primary Dependencies**: Django 6.1, Django REST Framework 3.18, django-filter,
drf-spectacular, django-auditlog, django-redis, djangorestframework-simplejwt,
django-constance, `numpy` (new explicit dependency for the preference math); Next.js
16.4, next-intl 4.x, HeroUI 3.2, TanStack Query (available; the catalog keeps its
server-fetch pattern)

**Storage**: PostgreSQL is the source of truth for preference profiles and signal
events; Redis caches the fitted plan space and serves DRF throttling. Plan data is read
from the existing `PublishedRecord` rows in `apps.catalog`.

**Testing**: pytest with `pytest-django` and Faker for the backend; Vitest with Testing
Library for the frontend. Regression tests cover the preference update, the merge
matrix, the signal endpoint, and the sort contract.

**Target Platform**: Linux server, Django WSGI backend; Next.js App Router server and
browser client.

**Project Type**: Web application — modular-monolith Django/DRF backend plus a Next.js
frontend in one repository.

**Performance Goals**: Sustain the constitution's 100 requests per second read-heavy
profile. Related ordering is an O(N) scoring pass over the filtered catalogue with a
cached fitted space; it must not add a database round trip per candidate.

**Constraints**: Cross-module access only through declared interfaces (constitution V);
every model soft-deleted and registered with django-auditlog (constitution, backend
rules); no repository abstraction over the ORM; generators used for scaffolding
(constitution XII); tunables (signal weights, decay, profile TTL, warm-up constants)
live in settings or django-constance, never hard-coded (constitution XIII); response
envelope and snake_case field names are mandatory.

**Scale/Scope**: One new backend application, two new models, one new client endpoint,
one catalogue behaviour change, five frontend touch points. The catalogue is expected
to stay in the thousands of published plans for this iteration.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| I. Product Domain | Related ordering serves search and comparison | PASS |
| II. Cost and External Resources | No new LLM or external spend | PASS |
| III. Security and Secrets | Device identity is an opaque random value; no fingerprinting; no personal data in profiles | PASS |
| IV. Data Governance | No new data stores outside Iran-hosted Postgres/Redis | PASS |
| V. Architecture | New app; catalog uses the recommendations interface only | PASS |
| VI. Performance and Scalability | O(N) scoring with a cached space; 100 RPS target respected | PASS |
| VII. Observability | Signal, merge, and ranking events logged as sampled structured JSON | PASS |
| VIII. Quality and Testing | Preference, merge, and sort behaviours get automated tests | PASS |
| IX. Data Retention | Profile TTL and signal retention configurable; no price-history impact | PASS |
| X. Crawling Ethics | Not affected | PASS |
| XI. Authentication | Reuses JWT OTP login; merge runs inside the existing sign-in transaction | PASS |
| XII. Established Libraries | Uses numpy, DRF, django-redis, django-constance, django-auditlog; app created with `startapp` | PASS with one tracked item (custom preference model, see Complexity Tracking) |
| XIII. Configurable Values | Weights, decay, TTL, and warm-up constants are settings/constance values | PASS |

**Gate result**: PASS with one tracked complexity item for the preference model.

## Project Structure

### Documentation (this feature)

```text
specs/005-related-plans-sort/
├── plan.md              # This file ($speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output ($speckit-tasks command - NOT created here)
```

### Source Code (repository root)

```text
backend/src/apps/
├── recommendations/                     # NEW application (created with `manage.py startapp`)
│   ├── __init__.py
│   ├── apps.py
│   ├── urls.py                          # mounts the signal endpoint under /api/v1/recommendations
│   ├── models/
│   │   ├── __init__.py                  # re-exports only
│   │   ├── interest_profile.py          # InterestProfile
│   │   └── interest_signal.py           # InterestSignal
│   ├── services/v1/
│   │   ├── __init__.py
│   │   ├── features.py                  # PlanFeatureMapper
│   │   ├── space.py                     # PlanSpace + NumericBinner (numpy)
│   │   ├── state.py                     # UserState (preference update)
│   │   ├── recommender.py               # distance + ordering
│   │   ├── store.py                     # InterestStateRepository (ORM + Redis space cache)
│   │   ├── signals.py                   # SignalRecorder + signal registry
│   │   ├── merging.py                   # StateMerger
│   │   └── ranking.py                   # RankingService facade
│   ├── serializers/v1/
│   │   ├── __init__.py
│   │   └── signals.py                   # SignalRequestSerializer, SignalResponseSerializer
│   ├── views/v1/
│   │   ├── __init__.py
│   │   └── signals.py                   # SignalViewSet
│   ├── interfaces.py                    # RecommendationsInterface (only cross-module surface)
│   ├── conf.py                          # settings/constance-backed tunables
│   ├── migrations/
│   └── tests/
│       ├── test_space.py
│       ├── test_state.py
│       ├── test_features.py
│       ├── test_ranking.py
│       ├── test_signals.py
│       ├── test_merging.py
│       └── v1/
│           └── test_signal_contract.py
├── catalog/
│   ├── views/v1/catalog.py              # MODIFIED: related sort + rank-before-paginate
│   └── tests/test_related_sort.py       # NEW: catalog-side contract tests
└── accounts/
    ├── services/v1/accounts.py          # MODIFIED: pass visitor identity into the sign-in transaction
    ├── views/v1/accounts.py             # MODIFIED: forward the visitor cookie to the service
    └── tests/test_login_merge.py        # NEW: merge-at-login regression

frontend/
├── middleware.ts                        # NEW: visitor cookie + x-visitor-id request header
└── src/
    ├── lib/
    │   ├── visitor.ts                   # NEW: server-side visitor identity helper
    │   └── api/
    │       ├── publicCatalog.ts         # MODIFIED: forward X-Visitor-Id server-side
    │       └── signals.ts               # NEW: signal client
    ├── features/home/
    │   ├── PlanCatalog.tsx              # MODIFIED: sort options prop + related default
    │   ├── SearchBox.tsx                # unchanged submit behaviour
    │   └── planCatalog/
    │       ├── CatalogControls.tsx      # MODIFIED: configurable sort options + label
    │       ├── PlanCard.tsx             # MODIFIED: emit details + destination signals
    │       └── SearchImpressionBeacon.tsx  # NEW: one signal per submitted query
    └── lib/i18n/messages/fa.json        # MODIFIED: related sort label

frontend/tests/
├── visitor.test.tsx                     # NEW
├── signals.test.ts                      # NEW
└── related-sort.test.tsx                # NEW
```

**Structure Decision**: The repository is a two-part web application (Django backend,
Next.js frontend). The preference domain is isolated in the new `apps.recommendations`
application so that `apps.catalog` and `apps.accounts` depend on it through
`RecommendationsInterface` only, satisfying constitution principle V.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Custom per-dimension preference model instead of an off-the-shelf recommender library | The model must work for anonymous device profiles with no interaction history, absorb three heterogeneous signals, and be cheap to update in-process. Maintained libraries that fit (implicit/ALS, LightFM, implicit-feedback) require user-item interaction matrices that do not exist for an anonymous device on its first visit and add a training pipeline for a demo-scale catalogue. | A simple popularity or "recently published" order cannot satisfy FR-002/FR-005 (per-viewer ordering with graded signal strength), and a collaborative-filtering library cannot produce the required deterministic cold-start order (FR-020). The Kalman-style update already exists as a prototype in `kalman_user_intent_detector.py`. |

## Phase 0: Outline & Research

Research tasks and resolved decisions are recorded in [research.md](./research.md).

## Phase 1: Design & Contracts

- Entities: [data-model.md](./data-model.md)
- HTTP contract: [contracts/recommendations-api.md](./contracts/recommendations-api.md)
- Validation guide: [quickstart.md](./quickstart.md)

## Post-Design Constitution Re-check

The Phase 1 design keeps the Phase 0 result. The new application owns its models and
services; the catalogue ranks through the interface; tunables live in
`apps/recommendations/conf.py` reading settings and constance; the two new models inherit
the shared soft-delete base and register with auditlog; no new external service or
credential is introduced. No new gate violations.
