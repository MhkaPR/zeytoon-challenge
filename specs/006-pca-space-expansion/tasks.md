---

description: "Task list for Periodic PCA Space Expansion"
---

# Tasks: Periodic PCA Space Expansion

**Input**: Design documents from `/specs/006-pca-space-expansion/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/space-cache.md

**Tests**: Included because Constitution VIII requires an automated test for every domain
behaviour.

**Organization**: Two user stories. US1 is the MVP; US2 hardens existing viewers and
failed refreshes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 or US2
- Exact file paths are included in every task

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add the dependency and configuration needed by both stories.

- [ ] T001 Add `scikit-learn` to the dependency list in `pyproject.toml` and run `uv sync`
- [ ] T002 [P] Add constance defaults `RECOMMENDATION_SEMANTIC_DIMENSIONS` (10), `RECOMMENDATION_SEMANTIC_N_FEATURES` (1024), `RECOMMENDATION_SEMANTIC_NGRAM_MIN` (2), `RECOMMENDATION_SEMANTIC_NGRAM_MAX` (4), and `RECOMMENDATION_SEMANTIC_RANDOM_STATE` (0) in `backend/src/config/settings/base.py`
- [ ] T003 [P] Add getters `semantic_dimensions()`, `semantic_n_features()`, `semantic_ngram_range()`, and `semantic_random_state()` in `backend/src/apps/recommendations/conf.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the semantic encoder and wire it into the existing plan space.

**⚠️ CRITICAL**: US1 and US2 cannot start until this phase is complete.

- [ ] T004 Implement `SemanticEncoder` in `backend/src/apps/recommendations/services/v1/semantic.py`: fit `HashingVectorizer(analyzer="char_wb", ngram_range=(ngram_min, ngram_max), n_features=semantic_n_features(), alternate_sign=False, norm="l2")` and `PCA(n_components=min(semantic_dimensions(), n_samples, n_features), random_state=semantic_random_state())`; min-max scale components to `[0, 1]` using fitted bounds; return `0.5` with mask `0` for empty titles; pad missing dimensions with `0.5`
- [ ] T005 [P] Add `title` to `PlanFeatureMapper.map` in `backend/src/apps/recommendations/services/v1/features.py`, reading `values["plan_name"]` then `values["title"]` then `values["name"]`
- [ ] T006 Integrate `SemanticEncoder` into `PlanSpace` in `backend/src/apps/recommendations/services/v1/space.py`: fit it in `fit()`, append `semantic_0` … `semantic_9` to `names`, append semantic values and masks in `transform()`, and include the title hash plus semantic configuration in `version()`
- [ ] T007 Add `PlanSpaceProvider.refresh(records)` in `backend/src/apps/recommendations/services/v1/store.py`: fit and validate the bundle, then write the versioned cache key; on failure log `recommendation_space_refresh_failed` and leave the existing key untouched

**Checkpoint**: The expanded space can be built and cached.

---

## Phase 3: User Story 1 - Ten semantic dimensions are added and refreshed (Priority: P1) 🎯 MVP

**Goal**: The cached space has ten semantic dimensions and a scheduled task refreshes it.

**Independent Test**: Run the refresh, inspect the cached space, and confirm ten
semantic dimensions and a new version. Record interest in one title theme and confirm
those plans rank higher.

### Tests for User Story 1

- [ ] T008 [P] [US1] Add `backend/src/apps/recommendations/tests/test_semantic.py` covering deterministic output, ten dimensions, `[0, 1]` bounds, empty-title neutrality, and a corpus smaller than the dimension count
- [ ] T009 [P] [US1] Update `backend/src/apps/recommendations/tests/test_space.py` to assert the space has ten `semantic_*` names, matching `values`/`masks` shapes, and a version that changes when a title or semantic setting changes
- [ ] T010 [P] [US1] Add a ranking test in `backend/src/apps/recommendations/tests/test_ranking.py` proving interest in plans sharing a title theme raises their rank after the semantic dimensions are present

### Implementation for User Story 1

- [ ] T011 [US1] Add `refresh_plan_space_task` in `backend/src/apps/recommendations/tasks.py` using `@task`; read plans through `CatalogInterface.published_plan_records()` and call `PlanSpaceProvider().refresh(records)` with structured start/success logs
- [ ] T012 [US1] Add `backend/src/apps/recommendations/management/commands/refresh_recommendation_space.py` that enqueues `refresh_plan_space_task` and prints the enqueue result
- [ ] T013 [US1] Run `uv run pytest backend/src/apps/recommendations/tests -q` for the files under `backend/src/apps/recommendations/tests/` and fix failures

**Checkpoint**: US1 is independently functional and testable.

---

## Phase 4: User Story 2 - Existing viewers and failed refreshes stay safe (Priority: P2)

**Goal**: Outdated profiles and failed refreshes never break catalogue requests.

**Independent Test**: Load a profile with the old dimension count and confirm the request
succeeds. Force a refresh failure and confirm the previous cache key is still served.

### Tests for User Story 2

- [ ] T014 [P] [US2] Add a test in `backend/src/apps/recommendations/tests/test_ranking.py` that a profile with an old `space_version` or wrong vector length is rebuilt from the cold-start prior and returns candidates without error
- [ ] T015 [P] [US2] Add `backend/src/apps/recommendations/tests/test_tasks.py` covering a successful refresh writing the cache and a failed refresh leaving the previous key and logging `recommendation_space_refresh_failed`

### Implementation for User Story 2

- [ ] T016 [US2] Confirm the existing reconciliation branches in `backend/src/apps/recommendations/services/v1/ranking.py` and `signals.py` handle the new dimension count; adjust only if the tests reveal a gap
- [ ] T017 [US2] Run `uv run pytest backend/src/apps/recommendations/tests backend/src/apps/catalog/tests -q` and fix failures

**Checkpoint**: US1 and US2 both work; feature 005 behaviour is preserved.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [ ] T018 [P] Update the module docstring in `backend/src/apps/recommendations/services/v1/semantic.py` and the tunables list in `backend/src/apps/recommendations/conf.py`
- [ ] T019 [P] Document the refresh command and cron cadence in `README.md`
- [ ] T020 Run the scenarios in `specs/006-pca-space-expansion/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup; blocks both user stories.
- **US1 (Phase 3)**: Depends on Foundational.
- **US2 (Phase 4)**: Depends on Foundational and benefits from US1's tests.
- **Polish (Phase 5)**: Depends on US1 and US2.

### Within Each Story

- Tests first, then implementation.
- `SemanticEncoder` before `PlanSpace` integration.
- `PlanSpace` integration before the refresh task.

### Parallel Opportunities

- T002 and T003 can run in parallel after T001.
- T005 can run in parallel with T004.
- T008, T009, and T010 can run in parallel.
- T014 and T015 can run in parallel.
- T018 and T019 can run in parallel.

---

## Parallel Example: User Story 1

```bash
Task: "Add semantic encoder tests in backend/src/apps/recommendations/tests/test_semantic.py"
Task: "Update space tests in backend/src/apps/recommendations/tests/test_space.py"
Task: "Add semantic ranking test in backend/src/apps/recommendations/tests/test_ranking.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2.
2. Complete US1.
3. Run `uv run pytest backend/src/apps/recommendations/tests -q`.
4. Validate the quickstart space inspection.

### Incremental Delivery

1. Setup + Foundational → expanded space builds.
2. US1 → scheduled refresh works (MVP).
3. US2 → outdated profiles and failed refreshes are safe.
4. Polish → docs and quickstart.

---

## Notes

- No new models or migrations.
- No public API change.
- Ranking and signal services should need no change; US2 only verifies that.
- Every task includes an exact file path.
