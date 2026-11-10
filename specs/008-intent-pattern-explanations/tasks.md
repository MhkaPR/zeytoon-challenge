# Tasks: Intent-Pattern Recommendation Explanations

**Input**: Design documents from `/specs/008-intent-pattern-explanations/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included because the specification's acceptance criteria explicitly require unit and regression tests.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (`US1`–`US5`)
- Include exact file paths in descriptions

## Path Conventions

- Backend: `backend/src/apps/...`
- Frontend: `frontend/src/...` and `frontend/tests/...`
- Feature docs: `specs/008-intent-pattern-explanations/...`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add the direct statistical dependency and replace obsolete explanation configuration.

- [ ] T001 Add `scipy>=1.18` to the project dependencies in `pyproject.toml` and run `uv sync`.
- [ ] T002 Replace the obsolete feature-explanation constance entries with `RECOMMENDATION_EXPLAIN_K=20`, `RECOMMENDATION_EXPLAIN_MIN_PATTERN_SIZE=30`, `RECOMMENDATION_EXPLAIN_ALPHA=0.05`, `RECOMMENDATION_EXPLAIN_MIN_LIFT=2.0`, `RECOMMENDATION_EXPLAIN_MIN_MCC=0.20`, and `RECOMMENDATION_EXPLAIN_MIN_CLICKS=3` in `backend/src/config/settings/base.py`.
- [ ] T003 Replace the obsolete accessor functions with `explain_min_pattern_size()`, `explain_alpha()`, `explain_min_lift()`, `explain_min_mcc()`, and `explain_min_clicks()` in `backend/src/apps/recommendations/conf.py`, keeping `explain_k()`.
- [ ] T004 [P] Create typed `ClusterIntentExplanation` and `PrimaryIntentExplanation` interfaces in `frontend/src/lib/api/intentExplanations.ts`.
- [ ] T005 [P] Confirm no `RecommendationExplanation` model reference remains and no new migration is required by running `python manage.py makemigrations --check --dry-run` against `backend/src/apps/recommendations/models/__init__.py`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the pattern registry, statistical scoring, and serializers that every user story depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Tests for Foundational Components

- [ ] T006 [P] Write registry tests asserting exactly `{cheap, value, spec_heavy, premium, exploring}`, no `text_specific`, correct predicates, and no numeric-range copy in `backend/src/apps/recommendations/tests/test_intent_patterns.py`.
- [ ] T007 [P] Write scoring tests for Gate 1 (`TP+FP < 30`), Gate 2 (`p > 0.05`), Gate 3 (`Lift < 2.0`), MCC filter (`|MCC| < 0.20`), MCC sign, ranking by `Lift × |MCC|`, and `exploring` exclusion in `backend/src/apps/recommendations/tests/test_intent_scoring.py`.

### Implementation for Foundational Components

- [ ] T008 [P] Implement the immutable `IntentPattern` definition, `PlanIntentFeatures` view, five-pattern `INTENT_PATTERNS` registry, positive/negative Persian messages, and `spec_pct` as the mean of present RAM/CPU/disk values in `backend/src/apps/recommendations/services/v1/intent_patterns.py`.
- [ ] T009 [P] Implement the contingency table, two-sided `scipy.stats.fisher_exact`, Lift, guarded MCC, gate evaluation, and `Lift × |MCC|` ranking in `backend/src/apps/recommendations/services/v1/intent_scoring.py`.
- [ ] T010 [P] Implement `ClusterIntentExplanationSerializer` and `PrimaryIntentExplanationSerializer` with nullable `direction`/`confidence` and `occurrence_count`/`cluster_count` fields in `backend/src/apps/recommendations/serializers/v1/intent_explanations.py`.

**Checkpoint**: Registry, scoring, and response serialization are ready for story integration.

---

## Phase 3: User Story 1 - The viewer sees an intent explanation, not an attribute range (Priority: P1) 🎯 MVP

**Goal**: Detect one intent per cluster from the top-K candidate set and expose the explanation in the suggested-plans response.

**Independent Test**: Seed a value-driven viewer with one cluster, load suggested plans, and confirm the response contains a `value` explanation with no numeric attribute range.

### Tests for User Story 1

- [ ] T011 [P] [US1] Write single-cluster explanation tests for candidate-set construction, pattern winner selection, corroboration, and no attribute-range leakage in `backend/src/apps/recommendations/tests/test_explanation.py`.

### Implementation for User Story 1

- [ ] T012 [US1] Implement per-cluster orchestration in `backend/src/apps/recommendations/services/v1/explanation.py`: build the top-K candidate set, evaluate real patterns, apply gates, corroborate against attributed destination-visit clicks, and return one explanation per cluster.
- [ ] T013 [US1] Implement nearest-cluster attribution of destination-visit clicks and the pattern-specific corroboration thresholds in `backend/src/apps/recommendations/services/v1/explanation.py`.
- [ ] T014 [US1] Add `suggest_with_explanations()` to `backend/src/apps/recommendations/services/v1/ranking.py`, computing explanations in the same request as plan selection.
- [ ] T015 [US1] Expose `suggest_with_explanations()` through `backend/src/apps/recommendations/interfaces.py`.
- [ ] T016 [US1] Update the suggested action in `backend/src/apps/catalog/views/v1/catalog.py` to serialize per-cluster intent explanations instead of feature reasons.
- [ ] T017 [US1] Update `SuggestedPlansResult` and response parsing in `frontend/src/lib/api/publicCatalog.ts` to consume the new explanation shape.
- [ ] T018 [US1] Update `frontend/src/features/home/SuggestedPlans.tsx` to render one intent message from the available explanation instead of feature reasons.
- [ ] T019 [US1] Replace the old feature-reason rendering tests with intent-message rendering tests in `frontend/tests/explanations.test.tsx`.

**Checkpoint**: A single-cluster viewer receives an intent explanation end to end.

---

## Phase 4: User Story 2 - The primary intent reflects the most frequent cluster intent (Priority: P1)

**Goal**: Aggregate per-cluster intents into one primary intent for the UI by occurrence count with deterministic tie-breaking.

**Independent Test**: Seed three clusters with detected intents `value`, `value`, `cheap`; confirm `primary_explanation.intent == "value"` and `occurrence_count == 2`.

### Tests for User Story 2

- [ ] T020 [P] [US2] Write primary-intent aggregation tests for occurrence counting, `exploring` exclusion, confidence tie-break, fixed-order tie-break, and highest-scoring cluster selection in `backend/src/apps/recommendations/tests/test_explanation.py`.

### Implementation for User Story 2

- [ ] T021 [US2] Implement `aggregate_primary_intent()` in `backend/src/apps/recommendations/services/v1/explanation.py` with the rules from FR-033–FR-038 and FR-041.
- [ ] T022 [US2] Wire `PrimaryIntentExplanationSerializer` into the suggested response in `backend/src/apps/recommendations/serializers/v1/intent_explanations.py`.
- [ ] T023 [US2] Add `primary_explanation` to the suggested action response in `backend/src/apps/catalog/views/v1/catalog.py`.
- [ ] T024 [US2] Extend `SuggestedPlansResult` and `getSuggestedPlans()` in `frontend/src/lib/api/publicCatalog.ts` to parse `primary_explanation`.
- [ ] T025 [US2] Update `frontend/src/features/home/SuggestedPlans.tsx` to render only the primary intent message and never one message per cluster.
- [ ] T026 [US2] Add frontend tests for primary-intent selection and single-message rendering in `frontend/tests/explanations.test.tsx`.

**Checkpoint**: Multi-cluster viewers see exactly one primary intent.

---

## Phase 5: User Story 3 - An honest fallback is used when no intent qualifies (Priority: P1)

**Goal**: Return `exploring` with null confidence whenever no real pattern passes every gate and corroboration check.

**Independent Test**: Seed a cold-start or random-click viewer and confirm `intent == "exploring"`, `direction == null`, and `confidence == null`.

### Tests for User Story 3

- [ ] T027 [P] [US3] Write fallback tests for cold-start profiles, random clicks, empty candidate sets, insufficient clicks, and all-clusters-exploring aggregation in `backend/src/apps/recommendations/tests/test_explanation.py`.

### Implementation for User Story 3

- [ ] T028 [US3] Implement the `exploring` fallback path, cold-start short-circuit, and null confidence/direction output in `backend/src/apps/recommendations/services/v1/explanation.py`.
- [ ] T029 [US3] Ensure `ClusterIntentExplanationSerializer` and `PrimaryIntentExplanationSerializer` accept null `direction` and null `confidence` in `backend/src/apps/recommendations/serializers/v1/intent_explanations.py`.
- [ ] T030 [US3] Add a frontend fallback-rendering test for the fixed exploring message in `frontend/tests/explanations.test.tsx`.

**Checkpoint**: Weak-evidence viewers receive an honest fallback, never a fabricated intent.

---

## Phase 6: User Story 4 - One source of truth for suggested plans and explanations (Priority: P2)

**Goal**: Remove the separate explanation endpoint and all feature-based explanation code so the suggested response is the only source.

**Independent Test**: Confirm `/api/v1/recommendations/explanations` returns 404 and no feature-reason formatter, serializer, or service remains.

### Tests for User Story 4

- [ ] T031 [P] [US4] Write an API contract test asserting `data`, `explanations`, and `primary_explanation` in one response and asserting the removed endpoint returns 404 in `backend/src/apps/catalog/tests/test_related_sort.py`.

### Implementation for User Story 4

- [ ] T032 [US4] Remove any remaining explanation route, model re-export, or admin reference from `backend/src/apps/recommendations/urls.py` and `backend/src/apps/recommendations/models/__init__.py`.
- [ ] T033 [US4] Delete `backend/src/apps/recommendations/services/v1/reasons.py` and `backend/src/apps/recommendations/serializers/v1/reasons.py`.
- [ ] T034 [US4] Delete `frontend/src/features/home/explanationText.ts`, `frontend/src/features/home/planCatalog/WhyRecommended.tsx`, and `frontend/src/lib/api/explanations.ts`.
- [ ] T035 [US4] Update imports in `frontend/src/features/home/SuggestedPlans.tsx`, `frontend/src/features/home/planCatalog/PlanCard.tsx`, and remove obsolete feature-range keys from `frontend/src/lib/i18n/messages/fa.json`.
- [ ] T036 [US4] Run `python manage.py makemigrations --check --dry-run` and confirm no new migration is generated for `backend/src/apps/recommendations/`.

**Checkpoint**: The suggested response is the single source of truth; old explanation code is gone.

---

## Phase 7: User Story 5 - Explanations are deterministic and configurable (Priority: P2)

**Goal**: Guarantee byte-identical output for the same profile and space version, with all thresholds runtime-configurable.

**Independent Test**: Request the same viewer twice and diff the responses; change `RECOMMENDATION_EXPLAIN_MIN_LIFT` and confirm the next response follows the new threshold.

### Tests for User Story 5

- [ ] T037 [P] [US5] Write determinism and configuration tests for repeated identical responses, stable tie-breaking, fixed confidence rounding, and runtime constance overrides in `backend/src/apps/recommendations/tests/test_explanation.py` and `backend/src/apps/recommendations/tests/test_intent_scoring.py`.

### Implementation for User Story 5

- [ ] T038 [US5] Enforce stable pattern/cluster ordering, deterministic candidate ordering, and fixed confidence rounding in `backend/src/apps/recommendations/services/v1/explanation.py` and `backend/src/apps/recommendations/services/v1/intent_scoring.py`.
- [ ] T039 [US5] Verify every threshold resolves through django-constance before Django settings and module defaults in `backend/src/apps/recommendations/conf.py`.
- [ ] T040 [US5] Run `yarn test explanations` and `yarn build` in `frontend/` to confirm deterministic rendering and a clean production build.

**Checkpoint**: Explanations are reproducible and operator-tunable.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, regression, performance, and end-to-end validation.

- [ ] T041 [P] Update the recommendation API and workflow docs in `backend/docs/recommendations/api.md` and `backend/docs/recommendations/workflow.md` to describe intent explanations and the removed endpoint.
- [ ] T042 Run the full backend suite with `.venv/bin/python -m pytest backend/src/apps/recommendations/tests backend/src/apps/catalog/tests -q` and fix regressions.
- [ ] T043 Run `yarn lint`, `yarn test`, and `yarn build` in `frontend/` and fix any new errors.
- [ ] T044 Run the validation scenarios in `specs/008-intent-pattern-explanations/quickstart.md`, including the removed-endpoint 404 and determinism diff.
- [ ] T045 Perform a performance sanity check in `backend/src/apps/recommendations/services/v1/explanation.py` and `backend/src/apps/recommendations/services/v1/intent_scoring.py`, confirming pattern masks are computed once per request, at most 16 Fisher tests run, and only one signal-history query is added.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Starts immediately.
- **Foundational (Phase 2)**: Depends on Setup and blocks all user stories.
- **User Stories (Phases 3–7)**: Depend on Foundational.
  - US1 and US2 are both P1; US2 depends on US1's per-cluster explanation output.
  - US3 depends on US1's scoring path and US2's aggregation.
  - US4 depends on US1–US3 so old code can be removed safely.
  - US5 depends on US1–US4.
- **Polish (Phase 8)**: Depends on all desired stories.

### User Story Dependencies

- **US1 (P1)**: No dependency on other stories after Foundational.
- **US2 (P1)**: Depends on US1 because it aggregates per-cluster results.
- **US3 (P1)**: Depends on US1 and US2 for the fallback and primary fallback.
- **US4 (P2)**: Depends on US1–US3 to avoid removing code still in use.
- **US5 (P2)**: Depends on US1–US4 for final determinism and configuration coverage.

### Within Each User Story

- Tests before implementation.
- Foundational registry/scoring before orchestration.
- Orchestration before API serialization.
- API serialization before frontend consumption.
- Story complete and validated before the next dependent story.

### Parallel Opportunities

- T004, T005 can run in parallel.
- T006, T007 can run in parallel.
- T008, T009, T010 can run in parallel.
- T011 can run while T008–T010 are being reviewed.
- T020 can run in parallel with T021–T023 once US1 is stable.
- T027 can run in parallel with T028–T029 once US1/US2 are stable.
- T031 can run in parallel with T032–T035 once the response contract is stable.
- T037 can run in parallel with T038–T039 once the core path is stable.
- T041 can run in parallel with T042–T045.

---

## Parallel Example: Foundational Components

```bash
# Launch registry, scoring, and serializer work together:
Task: "Implement intent_patterns.py"
Task: "Implement intent_scoring.py"
Task: "Implement intent_explanations.py serializers"
```

## Parallel Example: User Story 2

```bash
# After US1 is stable, run aggregation tests and serializer work together:
Task: "Write primary-intent aggregation tests"
Task: "Add PrimaryIntentExplanationSerializer"
Task: "Add primary_explanation to the catalog response"
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational.
3. Complete Phase 3: US1.
4. Validate one-cluster intent detection end to end.
5. Deploy/demo the MVP.

### Incremental Delivery

1. Setup + Foundational → registry and scoring ready.
2. US1 → per-cluster intent explanations.
3. US2 → single primary intent in the UI.
4. US3 → honest `exploring` fallback.
5. US4 → remove the old explanation path.
6. US5 → determinism and runtime configuration.
7. Polish → docs, regression, performance, quickstart.

### Parallel Team Strategy

1. One developer owns the pattern registry and scoring.
2. One developer owns the explanation orchestration and API.
3. One developer owns the frontend primary-intent rendering.
4. After US1 stabilizes, split US2/US3 and US4/US5 across developers.

---

## Notes

- Every task includes an exact file path.
- `[P]` tasks target different files and have no incomplete dependencies.
- Tests are required by the feature's acceptance criteria.
- Do not add a persisted explanation model or a new migration.
- Do not introduce a `text_specific` pattern.
- Validate that no explanation message contains a numeric range tied to a feature bin center.
