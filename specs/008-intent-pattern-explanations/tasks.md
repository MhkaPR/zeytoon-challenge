# Tasks: Intent-Pattern Recommendation Explanations

**Input**: Design documents from `/specs/008-intent-pattern-explanations/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included because the specification requires unit, API, and regression coverage.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story label (`US1`–`US5`)
- Every task includes an exact file path

---

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Add `scipy>=1.18.0` to `pyproject.toml`.
- [X] T002 Replace obsolete explanation constance entries with candidate size, pattern size, alpha, Lift, MCC, click count, question-form message catalog, and negative-intent flag in `backend/src/config/settings/base.py`.
- [X] T003 Add constance accessors for the new explanation settings in `backend/src/apps/recommendations/conf.py`.
- [X] T004 [P] Create the typed `ClusterIntentExplanation` contract in `frontend/src/lib/api/intentExplanations.ts`.
- [X] T005 Confirm no persisted explanation model or new migration is required in `backend/src/apps/recommendations/models/__init__.py`.

---

## Phase 2: Foundational (Blocking Prerequisites)

- [X] T006 [P] Test the five-key registry, predicates, question messages, and absence of `text_specific` in `backend/src/apps/recommendations/tests/test_intent_patterns.py`.
- [X] T007 [P] Test contingency tables, Fisher Exact, Lift, MCC, gates, ranking, and `exploring` exclusion in `backend/src/apps/recommendations/tests/test_intent_scoring.py`.
- [X] T008 [P] Implement the pattern registry and normalized feature view with no Persian strings in `backend/src/apps/recommendations/services/v1/intent_patterns.py`.
- [X] T009 [P] Implement statistical scoring and gates in `backend/src/apps/recommendations/services/v1/intent_scoring.py`.
- [X] T010 [P] Implement per-cluster intent serializers with `plan_ids`, nullable direction/confidence, in `backend/src/apps/recommendations/serializers/v1/intent_explanations.py`.

---

## Phase 3: User Story 1 - Each cluster shows its own intent explanation (Priority: P1) 🎯 MVP

**Goal**: Detect one intent per cluster and return its question plus its own plan list.

**Independent Test**: A value-driven cluster returns `value`, a question-form message, and its plan ids.

- [X] T011 [P] [US1] Test single-cluster winner selection, question messages, and per-cluster `plan_ids` in `backend/src/apps/recommendations/tests/test_explanation.py`.
- [X] T012 [US1] Implement per-cluster orchestration, candidate sets, pattern scoring, and plan grouping in `backend/src/apps/recommendations/services/v1/explanation.py`.
- [X] T013 [US1] Implement destination-visit corroboration and nearest-cluster click attribution in `backend/src/apps/recommendations/services/v1/explanation.py`.
- [X] T014 [US1] Add `suggest_with_explanations()` and load destination-visit signals in `backend/src/apps/recommendations/services/v1/ranking.py`.
- [X] T015 [US1] Expose `suggest_with_explanations()` in `backend/src/apps/recommendations/interfaces.py`.
- [X] T016 [US1] Serialize per-cluster intent explanations from the suggested action in `backend/src/apps/catalog/views/v1/catalog.py`.
- [X] T017 [US1] Parse the new explanation shape in `frontend/src/lib/api/publicCatalog.ts`.
- [X] T018 [US1] Render one section per explanation with its own plan row in `frontend/src/features/home/SuggestedPlans.tsx`.
- [X] T019 [US1] Test explanation sections and plan lists in `frontend/tests/explanations.test.tsx`.

---

## Phase 4: User Story 2 - Every cluster keeps its own intent, even when intents repeat (Priority: P1)

**Goal**: Return and render all cluster explanations, including repeated intents.

**Independent Test**: `value, value, cheap` produces three API entries and three UI sections.

- [X] T020 [P] [US2] Test repeated intents and cluster-order output in `backend/src/apps/recommendations/tests/test_explanation.py`.
- [X] T021 [US2] Ensure the API returns every explanation without aggregation in `backend/src/apps/recommendations/services/v1/explanation.py`.
- [X] T022 [US2] Ensure the catalog response returns the full explanations array in `backend/src/apps/catalog/views/v1/catalog.py`.
- [X] T023 [US2] Merge repeated intents and keep plan lists disjoint in `frontend/src/features/home/SuggestedPlans.tsx`.
- [X] T024 [US2] Test two value sections and one cheap section in `frontend/tests/explanations.test.tsx`.

---

## Phase 5: User Story 3 - An honest fallback is used when no intent qualifies (Priority: P1)

**Goal**: Return `exploring` per cluster when no real pattern qualifies, but hide it entirely in the UI.

**Independent Test**: Cold-start clusters return `exploring` with null confidence and no visible exploring question.

- [X] T025 [P] [US3] Test fallback and null confidence in `backend/src/apps/recommendations/tests/test_explanation.py`.
- [X] T026 [US3] Implement the per-cluster `exploring` fallback in `backend/src/apps/recommendations/services/v1/explanation.py`.
- [X] T027 [US3] Hide `exploring` explanations and their plans in `frontend/src/features/home/SuggestedPlans.tsx`.
- [X] T028 [US3] Test that exploring explanations and plans are hidden in `frontend/tests/explanations.test.tsx`.

---

## Phase 6: User Story 4 - One source of truth for suggested plans and explanations (Priority: P2)

**Goal**: Remove the separate explanation endpoint and all feature-based explanation code.

**Independent Test**: The old endpoint returns 404 and no feature-reason formatter remains.

- [X] T029 [P] [US4] Verify the suggested response contract in `backend/src/apps/catalog/tests/test_related_sort.py`.
- [X] T030 [US4] Remove old explanation routes/model references in `backend/src/apps/recommendations/urls.py` and `backend/src/apps/recommendations/models/__init__.py`.
- [X] T031 [US4] Delete `backend/src/apps/recommendations/services/v1/reasons.py` and `backend/src/apps/recommendations/serializers/v1/reasons.py`.
- [X] T032 [US4] Delete `frontend/src/features/home/explanationText.ts`, `frontend/src/features/home/planCatalog/WhyRecommended.tsx`, and `frontend/src/lib/api/explanations.ts`.
- [X] T033 [US4] Remove obsolete feature-range keys from `frontend/src/lib/i18n/messages/fa.json`.
- [X] T034 [US4] Confirm no new migration is generated for `backend/src/apps/recommendations/`.

---

## Phase 7: User Story 5 - Explanations are deterministic and configurable (Priority: P2)

**Goal**: Guarantee deterministic per-cluster output and runtime configuration.

- [X] T035 [P] [US5] Test deterministic ordering, rounding, and runtime thresholds in `backend/src/apps/recommendations/tests/test_explanation.py` and `backend/src/apps/recommendations/tests/test_intent_scoring.py`.
- [X] T036 [US5] Enforce stable cluster/pattern ordering and confidence rounding in `backend/src/apps/recommendations/services/v1/explanation.py` and `backend/src/apps/recommendations/services/v1/intent_scoring.py`.
- [X] T037 [US5] Verify messages and the negative-intent flag resolve through constance in `backend/src/apps/recommendations/conf.py`.
- [X] T038 [US5] Test the negative-intent flag in `backend/src/apps/recommendations/tests/test_explanation.py`.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T039 [P] Add a hidden-scrollbar plan row with previous/next controls in `frontend/src/features/home/planCatalog/PlanRow.tsx`.
- [X] T040 Use the plan row for every explanation and for the no-explanation fallback in `frontend/src/features/home/SuggestedPlans.tsx`.
- [X] T041 Update recommendation API/workflow docs in `backend/docs/recommendations/api.md` and `backend/docs/recommendations/workflow.md`.
- [X] T042 Run the backend recommendation and catalog regression suites.
- [X] T043 Run `yarn test explanations` in `frontend/`.
- [X] T044 Run the quickstart validation scenarios in `specs/008-intent-pattern-explanations/quickstart.md`.
- [X] T045 Confirm pattern masks are computed once per request and at most 16 Fisher tests run in `backend/src/apps/recommendations/services/v1/explanation.py` and `backend/src/apps/recommendations/services/v1/intent_scoring.py`.

---

## Dependencies & Execution Order

- Setup → Foundational → US1 → US2 → US3 → US4 → US5 → Polish.
- US2 depends on US1 because it renders the per-cluster output.
- US3 depends on US1/US2 for fallback rendering.
- US4 depends on US1–US3 so old code can be removed safely.
- US5 depends on the full per-cluster path.

## Notes

- No persisted explanation model or migration is introduced.
- No Persian strings live in backend service code; messages are constance-backed questions.
- `exploring` is fallback-only and its reason text is hidden in the UI.
- Repeated intents are merged into one row; plans never repeat across rows.
- Each explanation owns its plan list.
