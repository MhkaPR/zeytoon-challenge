# Tasks: Personalized Related Plans Ordering

**Input**: Design documents from `specs/005-related-plans-sort/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/recommendations-api.md](./contracts/recommendations-api.md), [quickstart.md](./quickstart.md)

**Tests**: Included. The project constitution (VIII) and `AGENTS.md` require an automated test for every domain behaviour and a regression test for every behaviour change, so test tasks are part of this feature.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US4)
- Every task lists the exact file path it touches

## Path Conventions

- Backend: `backend/src/apps/...`
- Frontend: `frontend/...`
- Specification artifacts: `specs/005-related-plans-sort/...`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the new application and declare dependencies.

- [X] T001 Add `numpy` as an explicit dependency in `pyproject.toml` and refresh `uv.lock` with `uv lock`
- [X] T002 Scaffold the new app with the framework generator (`cd backend/src && python manage.py startapp recommendations`) producing `backend/src/apps/recommendations/`, then register `apps.recommendations` in `backend/src/config/settings/base.py` `INSTALLED_APPS` and add `path("recommendations", include("apps.recommendations.urls"))` to `backend/src/config/api/v1/urls.py`
- [X] T003 [P] Create the versioned package skeleton and cross-module surface: `backend/src/apps/recommendations/services/v1/__init__.py`, `backend/src/apps/recommendations/serializers/v1/__init__.py`, `backend/src/apps/recommendations/views/v1/__init__.py`, `backend/src/apps/recommendations/interfaces.py`, `backend/src/apps/recommendations/conf.py`, `backend/src/apps/recommendations/urls.py`
- [X] T004 [P] Add the related-sort label key `sortRelated` («پیشنهاد برای شما») to `frontend/src/lib/i18n/messages/fa.json`
- [X] T005 [P] Add a `RecommendationsConfig` with a readable `verbose_name` in `backend/src/apps/recommendations/apps.py` and keep `__init__.py` re-export-only

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core models, preference math, identity transport, and configuration that every user story depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T006 Create `InterestProfile` in `backend/src/apps/recommendations/models/interest_profile.py` inheriting `TimestampedModel`: fields `user` (nullable FK), `visitor_id` (nullable UUID), `position` (JSON list of floats in `[0,1]`), `uncertainty` (JSON list of floats `>= 0`), `space_version` (string), `signal_count` (positive integer), `last_signal_at` (nullable datetime), `merged_into` (nullable FK to user); constraints: exactly one of `user`/`visitor_id` is non-null, partial unique index on `user` where `deleted_at IS NULL`, partial unique index on `visitor_id` where `deleted_at IS NULL`, and an index on `last_signal_at`
- [X] T007 [P] Create `InterestSignal` in `backend/src/apps/recommendations/models/interest_signal.py` inheriting `TimestampedModel`: fields `profile` (FK, required), `kind` (choices `destination_visit`, `details_view`, `search_impression`), `plan_ids` (JSON non-empty list of integers), `query` (nullable string, required only for `search_impression`), `weight` (float); indexes on `(profile, created_at)` and `kind`
- [X] T008 Re-export both models from `backend/src/apps/recommendations/models/__init__.py` and register both with `auditlog.register(...)` in `backend/src/apps/recommendations/apps.py`
- [X] T009 Generate and apply the app migration (`cd backend/src && python manage.py makemigrations recommendations && python manage.py migrate`); do not hand-edit migration files
- [X] T010 Implement `PlanSpace` and `NumericBinner` in `backend/src/apps/recommendations/services/v1/space.py` using numpy quantile/uniform bin edges, category lists, existence masks, and a stable dimension order
- [X] T011 [P] Implement `PlanFeatureMapper` in `backend/src/apps/recommendations/services/v1/features.py` mapping `PublishedRecord.values` to `price`, `cpu`, `ram`, `disk`, `traffic`, `country`, `os` and reusing `normalize_resource_value` / `RESOURCE_ALIASES` from `backend/src/apps/catalog/filters.py`
- [X] T012 [P] Implement `UserState` (position + per-dimension uncertainty, Kalman-style update with a predict/gain/measure cycle and ageing) in `backend/src/apps/recommendations/services/v1/state.py`
- [X] T013 [P] Implement all tunables in `backend/src/apps/recommendations/conf.py`: signal weights (`destination_visit` 0.3, `details_view` 0.8, `search_impression` 1.5), decay/ageing factor, profile TTL (180 days), per-viewer signal cap (30 per minute), and warm-up constants, read from Django settings with django-constance overrides; no hard-coded numbers in services
- [X] T014 Implement the ORM repository and Redis space cache in `backend/src/apps/recommendations/services/v1/store.py`: load/save/clear profiles by `visitor_id` or `user`, cache the fitted space under `recommendations:space:v1:<catalog_version>`, and derive the catalogue version from the latest publish timestamp and count of `PublishedRecord`
- [X] T015 Implement `Recommender` distances and ordering in `backend/src/apps/recommendations/services/v1/recommender.py`: distance over declared dimensions only, tie-break `(distance, -published_at, id)`, cold start = masked column mean identical for all viewers
- [X] T016 Define `RecommendationsInterface` in `backend/src/apps/recommendations/interfaces.py` exposing `rank`, `record_signals`, `merge_on_login`, and `clear_visitor`, and implement the delegation to the services without leaking internals; this is the only module other apps import
- [X] T017 Implement the ranged-signal throttle in `backend/src/apps/recommendations/views/v1/signals.py` using DRF `SimpleRateThrottle` keyed by identity and source, reading the configured per-minute cap
- [X] T018 Create `frontend/middleware.ts` to read `visitor_id` from the request cookie, generate `crypto.randomUUID()` when absent, set it on the response (httpOnly, `SameSite=Lax`, `Secure` in production, `path=/`, ~180-day max age), and inject `x-visitor-id` into the current request via `NextResponse.next({ request: { headers } })`; matcher excludes `_next`, static assets, and `/api`
- [X] T019 Implement `frontend/src/lib/visitor.ts` (server-side `visitorId()` reading the `x-visitor-id` header) and update `frontend/src/lib/api/publicCatalog.ts` so `getPlansPage` sends `X-Visitor-Id` to Django only when `typeof window === "undefined"`

**Checkpoint**: Models, preference math, identity transport, and tunables are ready.

---

## Phase 3: User Story 1 - Anonymous visitor sees a personalized default order (Priority: P1) 🎯 MVP

**Goal**: The main and company catalogues default to a related order computed from the device-scoped profile, deterministic at cold start.

**Independent Test**: Open the catalogue on two fresh devices and confirm the same order and the related option selected; record signals from the Quickstart, reload, and confirm the order shifts.

### Tests for User Story 1

- [X] T020 [P] [US1] Contract test for the related sort: omitted/`default` returns the masked-mean order, identical across two cold-start requests, in `backend/src/apps/catalog/tests/test_related_sort.py`
- [X] T021 [P] [US1] Unit test that undeclared attributes are masked and do not affect distance in `backend/src/apps/recommendations/tests/test_space.py` and `test_recommender.py`
- [ ] T022 [P] [US1] Frontend test that the default option is `default` with the related label and that page reload keeps the order in `frontend/tests/related-sort.test.tsx`

### Implementation for User Story 1

- [X] T023 [US1] Implement `RankingService` in `backend/src/apps/recommendations/services/v1/ranking.py`: accept the fitting corpus, the filtered candidate plan ids, and the resolved identity; fit or load the cached space; return plan ids ordered by distance
- [X] T024 [US1] Modify `PublishedPlansViewSet` in `backend/src/apps/catalog/views/v1/catalog.py`: keep `price`/`expensive` on the current SQL path, and for `default`/omitted filter first, rank the full matching set through `RecommendationsInterface`, then paginate the ordered list via the existing envelope paginator
- [X] T025 [P] [US1] Add a configurable options prop to `frontend/src/features/home/planCatalog/CatalogControls.tsx` and render the related label from the `sortRelated` catalog key
- [X] T026 [US1] Update `frontend/src/features/home/PlanCatalog.tsx` so the default sort is related, `resetFilters` restores related, and the toolbar forwards the options prop
- [X] T027 [P] [US1] Confirm `frontend/src/features/home/PlanCatalog.tsx` `buildParams` keeps sending `sort` only when it differs from `default`; leave the wire value `default` for backward compatibility
- [ ] T028 [US1] Add sampled structured logging for ranking (cache hit/miss, candidate count, cold-start flag) in `backend/src/apps/recommendations/services/v1/ranking.py`

**Checkpoint**: User Story 1 is independently functional and testable (MVP).

---

## Phase 4: User Story 2 - Interest signals refine the order (Priority: P1)

**Goal**: Destination visits, details views, and first-page search results update the profile with graded strength and bounded cumulative influence.

**Independent Test**: POST each signal kind for a plan and confirm the order moves toward it; confirm a destination visit moves it more than a search impression, and that a search with several results records one combined signal.

### Tests for User Story 2

- [ ] T029 [P] [US2] Contract test for `POST /api/v1/recommendations/signals` covering accepted/ignored/profile and validation errors in `backend/src/apps/recommendations/tests/v1/test_signal_contract.py`
- [X] T030 [P] [US2] Unit test graded weights and diminishing influence across repeated signals in `backend/src/apps/recommendations/tests/test_state.py`
- [X] T031 [P] [US2] Unit test that a multi-plan `search_impression` applies one centroid update in `backend/src/apps/recommendations/tests/test_signals.py`
- [ ] T032 [P] [US2] Throttle test that signals beyond the per-minute cap are reported as ignored, not accepted, in `backend/src/apps/recommendations/tests/test_signals.py`

### Implementation for User Story 2

- [X] T033 [P] [US2] Add `SignalRequestSerializer` (validates `kind`, non-empty `plan_ids`, and `query` required for `search_impression`) and `SignalResponseSerializer` in `backend/src/apps/recommendations/serializers/v1/signals.py`
- [X] T034 [US2] Implement `SignalRecorder` with a kind → weight registry in `backend/src/apps/recommendations/services/v1/signals.py`: resolve identity (authenticated user, else `visitor_id` cookie), redirect tombstoned device profiles to `merged_into`, load/update/save the profile, and append `InterestSignal` rows
- [X] T035 [US2] Implement `SignalViewSet` (create-only `GenericViewSet`) in `backend/src/apps/recommendations/views/v1/signals.py` with the serializer, throttle, `drf-spectacular` schema, and `{data: ...}` envelope; mount it in `backend/src/apps/recommendations/urls.py`
- [X] T036 [P] [US2] Implement `frontend/src/lib/api/signals.ts` with `sendSignal(kind, planIds, query?)` using `keepalive` and same-origin credentials
- [X] T037 [US2] Emit `details_view` on the details button and `destination_visit` on the outbound anchor in `frontend/src/features/home/planCatalog/PlanCard.tsx`
- [X] T038 [US2] Create `frontend/src/features/home/planCatalog/SearchImpressionBeacon.tsx` (client component firing one `search_impression` per submitted query with the page-1 plan ids) and mount it in `frontend/app/search/page.tsx`
- [X] T039 [P] [US2] Frontend test that `sendSignal` posts the expected payload and that no signal fires for an empty query in `frontend/tests/signals.test.ts`

**Checkpoint**: User Stories 1 and 2 work together; the order responds to real interactions.

---

## Phase 5: User Story 3 - Interest carries into the account on login (Priority: P2)

**Goal**: The sign-in hand-off folds the device profile into the account atomically; sign-out clears the device and keeps the account.

**Independent Test**: Record anonymous signals, sign in with a fresh phone, confirm continuity; sign out and confirm the cold-start order; sign in again and confirm the account order returns; repeat against an account that already has history.

### Tests for User Story 3

- [X] T040 [P] [US3] Unit test for the full merge matrix (account empty / account has history) in `backend/src/apps/recommendations/tests/test_merging.py`
- [X] T041 [P] [US3] Regression test that `POST /api/v1/auth/otp/verify` performs the hand-off inside one transaction and returns an unchanged body in `backend/src/apps/accounts/tests/test_login_merge.py`
- [ ] T042 [P] [US3] Test that a late signal for a tombstoned device profile is applied to the linked account in `backend/src/apps/recommendations/tests/test_signals.py`
- [ ] T043 [P] [US3] Test that the logout endpoint clears the device profile and cookie while keeping the account profile in `backend/src/apps/recommendations/tests/test_merging.py`

### Implementation for User Story 3

- [X] T044 [US3] Implement `StateMerger` in `backend/src/apps/recommendations/services/v1/merging.py`: under row locks, copy the device position/uncertainty to the account when the account has none, otherwise keep the account, then tombstone the device with `merged_into` set to the account
- [X] T045 [US3] Implement `merge_on_login` and `clear_visitor` in `backend/src/apps/recommendations/interfaces.py` delegating to `StateMerger` and the repository
- [X] T046 [US3] Extend `verify_otp` in `backend/src/apps/accounts/services/v1/accounts.py` with an optional `visitor_id=None` parameter and call `RecommendationsInterface.merge_on_login(user, visitor_id)` inside the existing `transaction.atomic()` block; keep the public signature backward compatible
- [X] T047 [US3] Forward the `visitor_id` cookie from `OtpVerifyViewSet.otp_verify` in `backend/src/apps/accounts/views/v1/accounts.py` into `services.verify_otp` without changing the response body
- [X] T048 [US3] Extend the logout action in `backend/src/apps/accounts/views/v1/accounts.py` to call `RecommendationsInterface.clear_visitor(visitor_id)` and clear the `visitor_id` cookie in the response, per `specs/005-related-plans-sort/contracts/recommendations-api.md` section 5

**Checkpoint**: All three delivery stories work; profiles follow the viewer across the sign-in boundary.

---

## Phase 6: User Story 4 - Existing sort behavior and search relevance are preserved (Priority: P2)

**Goal**: Price sorts and search relevance are unchanged; the related option is absent on search.

**Independent Test**: On the catalogue, cheapest is strictly ascending and most expensive strictly descending; on search, results stay relevance-ordered and the sort control exposes only price options.

### Tests for User Story 4

- [X] T049 [P] [US4] Test that `sort=price` and `sort=expensive` keep their existing SQL ordering and ignore the visitor header in `backend/src/apps/catalog/tests/test_related_sort.py`
- [ ] T050 [P] [US4] Frontend test that the search page offers only cheapest/most expensive and the catalogue offers all three in `frontend/tests/related-sort.test.tsx`

### Implementation for User Story 4

- [X] T051 [US4] Pass a price-only options list to `frontend/src/features/home/planCatalog/CatalogControls.tsx` from `frontend/app/search/page.tsx`, and keep the search default on query relevance
- [X] T052 [US4] Confirm `frontend/app/companies/[domain]/page.tsx` uses the related default and that `baseParams` filtering still narrows candidates before ranking

**Checkpoint**: The new default does not regress the comparator or search.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Operational concerns and end-to-end verification.

- [ ] T053 [P] Configure the retention sweep for profiles and signals (configurable TTL, default ~180 days) in `backend/src/apps/recommendations/tasks.py` using the Django Tasks framework
- [ ] T054 [P] Add sampled structured JSON logging for signal recording and merge events (no per-signal spam on hot paths) in `backend/src/apps/recommendations/services/v1/signals.py` and `merging.py`
- [ ] T055 [P] Ensure `drf-spectacular` describes the signal endpoint and the modified `sort` parameter in `backend/src/apps/recommendations/views/v1/signals.py` and `backend/src/apps/catalog/views/v1/catalog.py`
- [X] T056 Run the backend suites `uv run pytest backend/src/apps/recommendations/tests backend/src/apps/catalog/tests backend/src/apps/accounts/tests -q` and fix failures
- [ ] T057 Run the frontend gates for `frontend/` (`cd frontend && yarn test && yarn lint && yarn build`) and fix failures
- [ ] T058 Execute every scenario in [quickstart.md](./quickstart.md) end to end and record the results
- [ ] T059 [P] Update `README.md` and `backend/src/apps/recommendations/` module docstrings with the tunables and the identity header/cookie contract

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; T001 can start immediately.
- **Foundational (Phase 2)**: Depends on Setup; blocks all user stories.
- **User Stories (Phase 3+)**: Depend on Foundational.
  - US1 (P1) and US2 (P1) are the critical path; US2 is observable only once US1 rank-before-paginate ships, though its endpoint is independently testable.
  - US3 (P2) depends on the models and store (Phase 2), not on US1/US2 code.
  - US4 (P2) depends on US1's options prop.
- **Polish (Phase 7)**: Depends on all targeted stories.

### User Story Dependencies

- **US1**: Can start after Phase 2. No dependency on other stories.
- **US2**: Can start after Phase 2. Benefits from US1 for observable effect; independently testable via the endpoint.
- **US3**: Can start after Phase 2 (accounts touches are isolated to `verify_otp` and logout).
- **US4**: Depends on US1's `CatalogControls` options prop (T025).

### Within Each User Story

- Tests are written first and must fail before implementation.
- Models → repository → services → endpoints → frontend wiring.

### Parallel Opportunities

- Setup: T003, T004, T005 in parallel after T002.
- Foundational: T010–T013 in parallel; T018 and T019 in parallel after T002.
- US1: T020–T022 (tests) in parallel; T025 and T027 in parallel.
- US2: T029–T032 (tests) in parallel; T033, T036, T039 in parallel.
- US3: T040–T043 (tests) in parallel.
- US4: T049–T050 in parallel.

---

## Parallel Example: Foundational

```bash
Task: "Implement PlanSpace in backend/src/apps/recommendations/services/v1/space.py"
Task: "Implement PlanFeatureMapper in backend/src/apps/recommendations/services/v1/features.py"
Task: "Implement UserState in backend/src/apps/recommendations/services/v1/state.py"
Task: "Implement tunables in backend/src/apps/recommendations/conf.py"
```

## Parallel Example: User Story 2

```bash
Task: "Contract test signals endpoint in backend/src/apps/recommendations/tests/v1/test_signal_contract.py"
Task: "Unit test graded weights in backend/src/apps/recommendations/tests/test_state.py"
Task: "Unit test centroid search impression in backend/src/apps/recommendations/tests/test_signals.py"
Task: "Throttle test in backend/src/apps/recommendations/tests/test_signals.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup) and Phase 2 (Foundational).
2. Complete Phase 3 (US1) — the anonymous related default.
3. Stop and validate with quickstart Scenarios 1 and 5.
4. Deploy or demo the anonymous personalised default.

### Incremental Delivery

1. Setup + Foundational → foundation ready.
2. US1 → anonymous related default (MVP).
3. US2 → interaction signals refine the order.
4. US3 → sign-in continuity and privacy on sign-out.
5. US4 → confirm no regression to price sorts and search.
6. Polish → retention, observability, schema, and quickstart.

### Parallel Team Strategy

1. The team completes Setup + Foundational together (models and preference math are the shared bottleneck).
2. After Phase 2: one developer on US1 catalog ranking, one on US2 signal endpoint and frontend emitters, one on US3 merge and accounts integration.
3. US4 and Polish follow once US1's sort options ship.

---

## Notes

- `[P]` means different files with no dependency on an incomplete task.
- Every new domain behaviour ships with a test (constitution VIII).
- The related sort keeps the wire value `default`; only the label changes.
- Sign-in hand-off has no client endpoint (FR-018).
- The two new models are additive; reverting the app migration does not affect catalogue records.
