---

description: "Task list for Recommendation Explanations"
---

# Tasks: Recommendation Explanations

**Input**: Design documents from `/specs/007-recommendation-explanations/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/explanations.md, quickstart.md

**Tests**: Included. The project constitution (VIII) requires an automated test for every
domain behavior, so behaviour tests are part of each story.

**Organization**: Tasks are grouped by user story. Persistence of the space and explanation
results (FR-019–FR-022) is foundational because every story reads the persisted space.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are included in every task

## Path Conventions

Web application: `backend/src/` (Django/DRF) and `frontend/` (Next.js).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Configurable values and config accessors for the feature.

- [X] T001 Add constance tunables `RECOMMENDATION_EXPLANATION_FEATURE_COUNT` (int, default 3) and `RECOMMENDATION_EXPLANATION_RANGE_WIDTH` (float, default 0.1) to `CONSTANCE_CONFIG` in `backend/src/config/settings/base.py`
- [X] T002 [P] Add accessors `explanation_feature_count()` and `explanation_range_width()` plus defaults in `backend/src/apps/recommendations/conf.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Persist the recommendation space in PostgreSQL (source of truth) with Redis as a read-through cache. Blocks all user stories.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 [P] Create `RecommendationSpace` model in `backend/src/apps/recommendations/models/recommendation_space.py` with fields `version` (string, unique, indexed, non-empty), `names` (JSON), `values` (JSON), `masks` (JSON, same shape as values), `scales` (JSON, numeric min/max/edges + categorical vocabularies), `plan_ids` (JSON, same length as values), `published_at` (JSON, same length as values), `is_active` (bool), `plan_count` (int, non-negative); inherit the shared timestamped base model in `apps/utils`, use the custom soft-delete manager, and register with `auditlog`
- [X] T004 [P] Create `RecommendationExplanation` model in `backend/src/apps/recommendations/models/recommendation_explanation.py` with fields `profile` (FK → `InterestProfile`, required), `space_version` (string), `payload` (JSON, bounded by cluster cap), `computed_at` (auto datetime); inherit the shared timestamped base model, use the custom soft-delete manager, and register with `auditlog`
- [X] T005 Re-export the new models from `backend/src/apps/recommendations/models/__init__.py` and register both in `backend/src/apps/recommendations/admin.py`
- [X] T006 Generate the migration for the two models with `makemigrations recommendations` into `backend/src/apps/recommendations/migrations/` (never hand-edit the migration)
- [X] T007 Retain observed `min`/`max` on `NumericBinner` in `backend/src/apps/recommendations/services/v1/space.py` without changing existing `scale()` output, and expose min/max/edges plus categorical vocabularies for serialization
- [X] T008 Implement serialization/deserialization of a `PlanSpace` bundle (values, masks, names, scales, ids, timestamps, version) as model fields in `backend/src/apps/recommendations/services/v1/store.py`
- [X] T009 Convert `PlanSpaceProvider.load` in `backend/src/apps/recommendations/services/v1/store.py` to read-through: Redis cache → active `RecommendationSpace` DB row → build + persist; and make `refresh` write a new `RecommendationSpace` row, set it `is_active`, deactivate the previous version, and invalidate the Redis cache key (a failed rebuild MUST NOT replace the active row)
- [X] T010 [P] Add persistence tests in `backend/src/apps/recommendations/tests/test_space_persistence.py`: cold cache served from DB, refresh creates a new active version and invalidates cache, failed rebuild keeps the previous active row

**Checkpoint**: The space survives restarts and cache eviction; user stories can begin.

---

## Phase 3: User Story 1 - Each interest shows its closest plan with a reason (Priority: P1) 🎯 MVP

**Goal**: For every interest cluster the viewer holds, return the closest plan with one
explanation, persist it, and render it on the suggested-plans surface.

**Independent Test**: Record one interest signal, load the suggested strip, and confirm the
closest plan carries exactly one reason; a fresh viewer sees none.

### Tests for User Story 1

- [X] T011 [P] [US1] Add behaviour tests in `backend/src/apps/recommendations/tests/test_explanations.py`: one interest → exactly one explanation for the closest plan; several interests → one explanation per retained cluster; cold-start viewer → empty explanations and unchanged ranking order

### Implementation for User Story 1

- [X] T012 [US1] Implement a `FeatureGroup` classifier in `backend/src/apps/recommendations/services/v1/explanations.py` that maps `PlanSpace.names` to two categories: `semantic_*` → one textual group; `price`/`cpu`/`ram`/`disk`/`traffic` and `<field>=<value>` categoricals → individual technical groups; exclude `has_*` presence columns
- [X] T013 [US1] Implement the closest-plan + top-N selection in `backend/src/apps/recommendations/services/v1/explanations.py`: use `InterestClusters`/`Recommender` to pick each cluster's closest plan, score each eligible group by `1 - |position - plan_value|` under masks (textual = masked mean of the ten semantic dims), rank descending, keep `explanation_feature_count()`, break ties by dimension name
- [X] T014 [US1] Build `ClusterExplanation` objects (`plan_id` + ordered `matches`) in `backend/src/apps/recommendations/services/v1/explanations.py`, with `matches[].category`, `matches[].kind`, `name`/`label`, and a `ServiceExplanations.for_viewer(records, visitor_id, user)` entry point
- [X] T015 [US1] Persist and read through explanations: write a `RecommendationExplanation` row on first computation per `(profile, space_version)` and re-read it on later calls in `backend/src/apps/recommendations/services/v1/explanations.py`
- [X] T016 [US1] Expose the explanation call on `RecommendationsInterface` in `backend/src/apps/recommendations/interfaces.py`
- [X] T017 [P] [US1] Add `ExplanationRequestSerializer`/`ExplanationResponseSerializer` in `backend/src/apps/recommendations/serializers/v1/explanations.py` (envelope `{"data": {...}}`, `snake_case`)
- [X] T018 [US1] Add the read-only endpoint in `backend/src/apps/recommendations/views/v1/explanations.py` (ViewSet, no `APIView`) resolving identity from session → `X-Visitor-Id` → `visitor_id` cookie, and register the route in `backend/src/apps/recommendations/urls.py`
- [X] T019 [US1] Add a typed `getRecommendationExplanations({ visitorId })` client in `frontend/src/lib/api/explanations.ts`
- [X] T020 [US1] Render the reason on the matching card in `frontend/src/features/home/SuggestedPlans.tsx` (pass the explanation to the closest plan's card)
- [X] T021 [US1] Add explanation message templates to `frontend/src/lib/i18n/messages/fa.json`

**Checkpoint**: User Story 1 is fully functional and testable independently (MVP).

---

## Phase 4: User Story 2 - The reason names the features the viewer actually matched (Priority: P1)

**Goal**: Revert normalized values to real units and phrase textual vs technical matches
correctly and deterministically.

**Independent Test**: For a technical-closest viewer the sentence names the attribute with a
real-unit range; for a textual-closest viewer it describes a product category; identical
state yields identical text.

### Tests for User Story 2

- [X] T022 [P] [US2] Add behaviour tests in `backend/src/apps/recommendations/tests/test_explanations.py`: textual-closest yields no numbers; technical numeric yields a clamped real-unit range; at most the configured number of names; repeated calls are byte-identical

### Implementation for User Story 2

- [X] T023 [US2] Implement value reverting in `backend/src/apps/recommendations/services/v1/explanations.py`: for numeric technical matches, revert the normalized position via the containing bin and quote `low`/`high` widened by `explanation_range_width()` and clamped to the observed `[min, max]`; for categorical matches set `label`; for textual matches set `label` and set `has_textual`
- [X] T024 [US2] Enforce determinism in `backend/src/apps/recommendations/services/v1/explanations.py`: stable dimension order, tie-break by name, fixed rounding on ranges, no clock/request-order input
- [X] T025 [US2] Update `frontend/src/lib/api/explanations.ts` and `frontend/src/features/home/SuggestedPlans.tsx` to build the localized sentence from `matches` (textual → product-category phrasing; numeric → attribute + range + unit; categorical → category name)
- [X] T026 [P] [US2] Add rendering tests in `frontend/tests/explanations.test.tsx`: textual vs technical phrasing differs, ranges render with units, no raw scores appear

**Checkpoint**: Reasons name real matched features and are deterministic.

---

## Phase 5: User Story 3 - Explanations survive cluster and space changes (Priority: P2)

**Goal**: Keep explanations correct and bounded across the cluster cap, space refresh, and
missing data.

**Independent Test**: Drive the profile past the cluster maximum, refresh the space, and
confirm explanations stay one-per-interest, never exceed the cap, and never break on
outdated profiles.

### Tests for User Story 3

- [X] T027 [P] [US3] Add behaviour tests in `backend/src/apps/recommendations/tests/test_explanations.py`: never more explanations than the cluster cap; duplicate closest plans collapse to one; outdated `space_version` recomputes instead of serving; missing attribute omitted, not zeroed

### Implementation for User Story 3

- [X] T028 [US3] Bound and dedupe explanations in `backend/src/apps/recommendations/services/v1/explanations.py`: one per retained cluster, cap at `RECOMMENDATION_MAX_INTEREST_CLUSTERS`, dedupe by `plan_id` keeping the closer cluster, and skip clusters still on the cold-start prior
- [X] T029 [US3] Handle version and missing-data safety in `backend/src/apps/recommendations/services/v1/explanations.py`: recompute a `RecommendationExplanation` whose `space_version` is stale, omit masked/missing attributes from matches, and never raise on outdated profiles or empty titles

**Checkpoint**: All three stories work independently.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Observability, docs, and end-to-end validation.

- [X] T030 [P] Add sampled structured logging for explanation generation in `backend/src/apps/recommendations/services/v1/explanations.py` (event name + counts; no per-plan loop logging)
- [X] T031 [P] Confirm `drf-spectacular` documents the new endpoint via `extend_schema` in `backend/src/apps/recommendations/views/v1/explanations.py`
- [X] T032 Run `uv run pytest backend/src/apps/recommendations backend/src/apps/catalog -q` and `cd frontend && yarn test explanations` and resolve failures
- [ ] T033 Run the quickstart end-to-end scenarios in `specs/007-recommendation-explanations/quickstart.md` (including the cache-eviction persistence check) and record results

---

## Implementation Notes (2026-11-09)

- T001–T032 complete. Backend: `backend/src/apps/recommendations` and
  `backend/src/apps/catalog` suites pass (52 tests). Frontend `explanations` suite passes
  (6 tests); `yarn lint` reports 0 errors.
- T033 not run in-session: the quickstart's manual `runserver`/`yarn dev` steps need a
  bindable port, which the sandbox blocks. The equivalent automated persistence check is
  covered by `test_space_persistence.py`.
- Pre-existing, unrelated failures remain in `backend/src/apps/pipeline` (11 tests:
  retry/dead-letter and replay-scheduler behaviour) and two frontend tests
  (`plan-card.test.tsx` "otherAttributes" region, `search-box.test.tsx`). None touch the
  files changed by this feature.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup; BLOCKS all user stories.
- **User Stories (Phase 3+)**: Depend on Foundational.
  - US1 (P1) first (MVP); US2 (P1) builds on US1's service; US3 (P2) hardens US1/US2.
- **Polish (Phase 6)**: After desired stories are complete.

### User Story Dependencies

- **US1 (P1)**: After Foundational; no dependency on other stories.
- **US2 (P1)**: After Foundational; extends US1's `explanations.py` (shares the file, so sequence after T012–T015).
- **US3 (P2)**: After Foundational; hardens US1/US2 (shares `explanations.py`).

### Within Each User Story

- Tests before implementation; verify they fail first.
- Model/classifier before service; service before endpoint; endpoint before UI.

### Parallel Opportunities

- T001/T002 in Setup can run together; T003/T004 models are independent files.
- T010, T011, T022, T026, T027 test files for different concerns can be written in parallel.
- T017 (serializer) is independent of the service internals.

---

## Parallel Example: User Story 1

```bash
# Independent files that can be prepared together:
Task: "Add ExplanationRequestSerializer/ExplanationResponseSerializer in backend/src/apps/recommendations/serializers/v1/explanations.py"
Task: "Add behaviour tests in backend/src/apps/recommendations/tests/test_explanations.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup → Phase 2 Foundational (persistence) → Phase 3 US1.
2. STOP and validate US1 via T011 and the quickstart suggested-strip scenario.

### Incremental Delivery

1. Foundational persistence → restarts/cache eviction safe.
2. US1 → closest plan + reason rendered (MVP).
3. US2 → real-unit, deterministic wording.
4. US3 → cap, dedupe, version safety.

---

## Notes

- [P] tasks touch different files and have no incomplete dependencies.
- Every task includes an exact file path.
- Tests are constitution-mandated (Principle VIII), not optional here.
- No hand-edited migrations; generate with `makemigrations`.
