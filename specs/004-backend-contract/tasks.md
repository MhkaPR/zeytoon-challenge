---

description: "Task list for Backend Development Contract Compliance"
---

# Tasks: Backend Development Contract Compliance

**Input**: Design documents from `specs/004-backend-contract/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/api-conventions.md](./contracts/api-conventions.md)

**Tests**: Included because the spec requires a regression test for every behavior change (FR-038).

**Organization**: Tasks are grouped by user story so each story can be implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US6)
- Every task includes an exact file path

## Path Conventions

- Backend root: `backend/src/`
- Application package: `backend/src/apps/`
- Project package: `backend/src/config/`
- Frontend client: `frontend/`
- Production image: `Dockerfile` at the repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the pipeline application skeleton and align shared configuration.

- [ ] T001 Create the pipeline application skeleton with `apps.py`, `__init__.py`, `models/`, `views/v1/`, `serializers/v1/`, `services/v1/`, `tests/`, `admin.py`, `tasks.py`, and `interfaces.py` under `backend/src/apps/pipeline/`
- [ ] T002 [P] Add `faker` to the dev dependency group in `pyproject.toml`
- [ ] T003 [P] Create the production `Dockerfile` at the repository root from the existing `backend/Dockerfile`, keeping the backend build context
- [ ] T004 [P] Verify `.env.dist` documents `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DATABASE_URL`, `REDIS_URL`, and the storage variables
- [ ] T005 [P] Add `apps.pipeline` and remove `apps.notifications` in `INSTALLED_APPS` in `backend/src/config/settings/base.py`
- [ ] T006 [P] Remove the `apps.notifications.urls` include from `backend/src/config/api/v1/urls.py`
- [ ] T007 [P] Update the audit `project_apps` set in `backend/src/apps/utils/apps.py` to include `pipeline` and drop `notifications`
- [ ] T008 [P] Set `DEFAULT_PERMISSION_CLASSES` to `IsAuthenticated`, add a default page-size pagination class, and add `DjangoFilterBackend`, `SearchFilter`, and `OrderingFilter` in `backend/src/config/settings/base.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared infrastructure that every user story depends on.

**⚠️ CRITICAL**: Complete this phase before starting any user story.

- [ ] T009 Verify `TimestampedModel` exposes `created_at`, `updated_at`, and `deleted_at` (`deleted_at` nullable) in `backend/src/apps/utils/models/base.py`
- [ ] T010 Verify `SoftDeleteManager.objects` excludes records with `deleted_at` set, `DeletedObjectsManager.deleted_objects` includes only deleted records, `delete()` soft-deletes, and `hard_delete()` physically deletes in `backend/src/apps/utils/models/soft_delete.py`
- [ ] T011 [P] Keep the shared DRF input helper in `backend/src/apps/utils/serializers.py` and remove any Pydantic fallback from it
- [ ] T012 [P] Verify the JSON logging formatter and sensitive-data filter in `backend/src/apps/utils/logging.py` and the `LOGGING` setting in `backend/src/config/settings/base.py`
- [ ] T013 [P] Verify the `TASKS` setting in `backend/src/config/settings/base.py` selects the backend from configuration and does not hard-code it in application code
- [ ] T014 [P] Verify the `drf-spectacular` schema and Swagger routes in `backend/src/config/urls.py`
- [ ] T015 Create a shared Django `unittest` base test case using Faker in `backend/src/apps/utils/testing.py`
- [ ] T016 Run `python manage.py check` from `backend/src/` and resolve import or configuration errors

**Checkpoint**: Shared infrastructure is ready; user stories can begin.

---

## Phase 3: User Story 1 - Predictable project structure and environment (Priority: P1) 🎯 MVP

**Goal**: Every application follows the documented layout and environment settings.

**Independent Test**: Inspect each application for the required directories and start the development server from a clean checkout.

### Tests for User Story 1

- [ ] T017 [P] [US1] Add a layout test that asserts every application has `models/`, `views/v1/`, `serializers/v1/`, `services/v1/`, and `tests/` in `backend/src/apps/utils/tests/test_layout.py`
- [ ] T018 [P] [US1] Add a test that asserts every `models/__init__.py` re-exports classes and defines no model class in `backend/src/apps/utils/tests/test_models_init.py`

### Implementation for User Story 1

- [ ] T019 [US1] Audit `backend/src/apps/accounts/`, `backend/src/apps/companies/`, `backend/src/apps/catalog/`, `backend/src/apps/admin_console/`, and `backend/src/apps/pipeline/` and create any missing versioned directories
- [ ] T020 [US1] Move loose view modules into `views/v1/` and update imports in each application's `urls.py`
- [ ] T021 [US1] Move loose serializer modules into `serializers/v1/` and update imports
- [ ] T022 [US1] Move loose service modules into `services/v1/` and update imports
- [ ] T023 [US1] Verify `backend/src/config/settings/__init__.py` selects development settings and `dev.py`/`prod.py` import `base.py`
- [ ] T024 [US1] Verify `backend/src/manage.py` sits beside `apps/` and `config/` and only bootstraps Django
- [ ] T025 [US1] Run the layout tests and `python manage.py check` from `backend/src/`

**Checkpoint**: The project layout matches the contract.

---

## Phase 4: User Story 6 - Pipeline domain separated from the operator console (Priority: P1)

**Goal**: Move the crawl-to-publish domain into `apps/pipeline`, remove notifications, and keep the admin console as the operator surface.

**Independent Test**: Confirm `apps/pipeline` owns all pipeline models, services, tasks, and helpers; `apps/admin_console` owns no pipeline model; and `apps/notifications` is gone.

### Tests for User Story 6

- [ ] T026 [P] [US6] Add a test that asserts `apps.pipeline` owns the site, link, capture, trace, table, classification, plan, replay, alert, and cost-ledger models in `backend/src/apps/pipeline/tests/test_module_boundaries.py`
- [ ] T027 [P] [US6] Add a test that asserts `apps.admin_console` has no pipeline model or stage service in `backend/src/apps/admin_console/tests/test_module_boundaries.py`
- [ ] T028 [P] [US6] Add a test that asserts `apps.notifications` is absent and no settings or URL module references it in `backend/src/apps/utils/tests/test_notifications_removed.py`

### Implementation for User Story 6

- [ ] T029 [US6] Move `Site`, `Link`, `CaptureSession`, `Trace`, `ExtractedTable`, `ExtractedTableColumn`, `ExtractedTableRow`, `TableClassification`, `ClassificationRegex`, `PlanRecord`, `PlanExclusion`, `SemanticLabel`, `ReplayRun`, `ChangeRecord`, `FailureAlert`, and `LlmCostLedger` model modules from `backend/src/apps/admin_console/models/` to `backend/src/apps/pipeline/models/`
- [ ] T030 [US6] Update every foreign key string from `admin_console.<Model>` to `pipeline.<Model>` and every `apps.admin_console.models` import to `apps.pipeline.models` across `backend/src/apps/pipeline/models/`
- [ ] T031 [US6] Move `artifacts.py`, `constants.py`, `discovery.py`, `domtrack_client.py`, `events.py`, `llm.py`, `plan_schema.py`, `replay.py`, and `table_classifier.py` from `backend/src/apps/admin_console/` to `backend/src/apps/pipeline/`
- [ ] T032 [US6] Move the pipeline stage services from `backend/src/apps/admin_console/services/v1/admin_console.py` to `backend/src/apps/pipeline/services/v1/pipeline.py`, keeping approval-queue and verification-decision services in `backend/src/apps/admin_console/services/v1/admin_console.py`
- [ ] T033 [US6] Move pipeline tasks from `backend/src/apps/admin_console/tasks.py` to `backend/src/apps/pipeline/tasks.py` and update task path strings to `pipeline.tasks.*`
- [ ] T034 [US6] Move pipeline tests from `backend/src/apps/admin_console/tests/` to `backend/src/apps/pipeline/tests/`, keeping approval and console tests in `backend/src/apps/admin_console/tests/`
- [ ] T035 [US6] Create `PipelineInterface` in `backend/src/apps/pipeline/interfaces.py` exposing link/site summaries, pipeline task enqueue helpers, and the stage operations the operator console needs
- [ ] T036 [US6] Update `backend/src/apps/admin_console/services/v1/admin_console.py` and `backend/src/apps/admin_console/views/v1/admin_console.py` to call `PipelineInterface` or pipeline services instead of importing pipeline models directly
- [ ] T037 [US6] Delete `backend/src/apps/notifications/` and remove notification imports from `backend/src/apps/pipeline/services/v1/pipeline.py`, `backend/src/apps/pipeline/llm.py`, and `backend/src/apps/pipeline/tasks.py`
- [ ] T038 [US6] Remove `notification_dedup_key` writes from the failure-alert path in `backend/src/apps/pipeline/services/v1/pipeline.py`
- [ ] T039 [US6] Generate migrations for the app-label move with `python manage.py makemigrations pipeline` and `python manage.py makemigrations admin_console` from `backend/src/`
- [ ] T040 [US6] Verify the moved models keep their existing database table names unless the contract explicitly approves a rename in `backend/src/apps/pipeline/models/`
- [ ] T041 [US6] Run the module-boundary tests in `backend/src/apps/pipeline/tests/test_module_boundaries.py` and `backend/src/apps/admin_console/tests/test_module_boundaries.py` and resolve failures

**Checkpoint**: Pipeline and admin console are separated, notifications are gone, and the module-boundary tests pass.

---

## Phase 5: User Story 2 - Consistent, documented API behavior (Priority: P1)

**Goal**: Every endpoint is a generic viewset action, every response is serializer-produced, every request is DRF-validated, and the envelope is consistent.

**Independent Test**: Call a collection and a detail endpoint, confirm `data`/`page`, submit invalid input, and open the generated schema.

### Tests for User Story 2

- [ ] T042 [P] [US2] Add contract tests for the `data`/`page` envelope in `backend/src/apps/admin_console/tests/v1/test_envelope.py`
- [ ] T043 [P] [US2] Add contract tests for serializer validation errors in `backend/src/apps/admin_console/tests/v1/test_validation.py`
- [ ] T044 [P] [US2] Add a test that asserts no API or serializer module imports Pydantic in `backend/src/apps/utils/tests/test_no_pydantic_api.py`

### Implementation for User Story 2

- [ ] T045 [US2] Rewrite `backend/src/apps/admin_console/serializers/v1/admin_console.py` to use only DRF serializers and remove every Pydantic model and `parse_input`
- [ ] T046 [US2] Add input serializers for verification decisions, site creation, discovery bounds, manual links, capture start, classification, plans, plan ignore, replay runs, settings updates, and token budget in `backend/src/apps/admin_console/serializers/v1/admin_console.py`
- [ ] T047 [US2] Add output serializers for sites, links, capture sessions, tables, classifications, plans, replay runs, alerts, failure status, token budget, metrics, and settings in `backend/src/apps/admin_console/serializers/v1/admin_console.py`
- [ ] T048 [US2] Rewrite `backend/src/apps/admin_console/views/v1/admin_console.py` as `GenericViewSet`/`ModelViewSet` classes with `@action` methods and remove the deleted `ActionViewSet` import
- [ ] T049 [US2] Convert `backend/src/apps/admin_console/urls.py` to a DRF router and preserve the existing `/api/v1/ops/` URL names used by the frontend
- [ ] T050 [US2] Ensure every view in `backend/src/apps/admin_console/views/v1/admin_console.py` returns `Response(serializer.data)` or a serializer-produced envelope, with no hand-built response dictionaries
- [ ] T051 [US2] Apply the same serializer-first rule to `backend/src/apps/accounts/views/v1/accounts.py`, `backend/src/apps/companies/views/v1/companies.py`, and `backend/src/apps/catalog/views/v1/catalog.py`
- [ ] T052 [US2] Add a shared envelope helper or serializer base in `backend/src/apps/utils/serializers.py` so list and detail responses use `data` and optional `page`
- [ ] T053 [US2] Update `frontend/src/lib/api/ops.ts` to read `data` and `page` instead of `results`
- [ ] T054 [US2] Verify `python manage.py spectacular --file /tmp/schema.yaml` from `backend/src/` succeeds and lists the versioned endpoints
- [ ] T055 [US2] Run the envelope, validation, and no-Pydantic tests in `backend/src/apps/admin_console/tests/v1/test_envelope.py`, `backend/src/apps/admin_console/tests/v1/test_validation.py`, and `backend/src/apps/utils/tests/test_no_pydantic_api.py`

**Checkpoint**: The API boundary is serializer-first and documented.

---

## Phase 6: User Story 3 - Safe data lifecycle and change history (Priority: P1)

**Goal**: Every model is soft-deleted and audited, and every schema change is a new migration.

**Independent Test**: Soft-delete a record, confirm manager behavior and audit entries, then confirm `makemigrations --check` reports no drift.

### Tests for User Story 3

- [ ] T056 [P] [US3] Add soft-delete tests for `objects`, `deleted_objects`, `delete()`, and `hard_delete()` in `backend/src/apps/utils/tests/test_soft_delete.py`
- [ ] T057 [P] [US3] Add audit tests for create, update, and delete in `backend/src/apps/utils/tests/test_audit.py`
- [ ] T058 [P] [US3] Add a test that asserts every domain model inherits `TimestampedModel` in `backend/src/apps/utils/tests/test_model_base.py`

### Implementation for User Story 3

- [ ] T059 [US3] Audit `backend/src/apps/accounts/models/`, `backend/src/apps/companies/models/`, `backend/src/apps/catalog/models/`, and `backend/src/apps/pipeline/models/` and make every model inherit `TimestampedModel`
- [ ] T060 [US3] Verify `backend/src/apps/utils/apps.py` registers every domain model with `auditlog.register`
- [ ] T061 [US3] Generate new migrations for any model base or field changes with `python manage.py makemigrations` from `backend/src/`
- [ ] T062 [US3] Run `python manage.py makemigrations --check --dry-run` from `backend/src/` and resolve all pending changes
- [ ] T063 [US3] Audit cross-application imports in `backend/src/apps/` and replace direct model access with the owning application's interface where the constitution requires it
- [ ] T064 [US3] Run the soft-delete, audit, and model-base tests in `backend/src/apps/utils/tests/test_soft_delete.py`, `backend/src/apps/utils/tests/test_audit.py`, and `backend/src/apps/utils/tests/test_model_base.py`

**Checkpoint**: The data lifecycle is safe and auditable.

---

## Phase 7: User Story 4 - Operable, secure, and testable delivery (Priority: P2)

**Goal**: Tasks, logging, security, tests, and the production image meet the contract.

**Independent Test**: Enqueue a task, inspect a JSON log line, run the test suite, and build the production image.

### Tests for User Story 4

- [ ] T065 [P] [US4] Add a task test that asserts tasks are enqueued through the configured backend in `backend/src/apps/pipeline/tests/test_tasks.py`
- [ ] T066 [P] [US4] Add a logging test that asserts JSON output and sensitive-data masking in `backend/src/apps/utils/tests/test_logging.py`
- [ ] T067 [P] [US4] Add an authorization test that asserts public endpoints allow anonymous access and operator endpoints require an operator permission in `backend/src/apps/admin_console/tests/v1/test_authorization.py`

### Implementation for User Story 4

- [ ] T068 [US4] Replace the global `AllowAny` default with `IsAuthenticated` in `backend/src/config/settings/base.py`
- [ ] T069 [US4] Add explicit `AllowAny` permission classes to public endpoints in `backend/src/apps/accounts/views/v1/accounts.py`, `backend/src/apps/companies/views/v1/companies.py`, and `backend/src/apps/catalog/views/v1/catalog.py`
- [ ] T070 [US4] Create an operator permission class backed by Django groups or django-guardian in `backend/src/apps/admin_console/permissions.py` and use it on operator viewsets
- [ ] T071 [US4] Verify every task in `backend/src/apps/pipeline/tasks.py` uses `@task` and every caller uses `.enqueue()`
- [ ] T072 [US4] Verify the JSON formatter and `LOG_LEVEL` default in `backend/src/config/settings/base.py`
- [ ] T073 [US4] Migrate the backend test suite from pytest-style functions to Django `unittest` classes under each application's `tests/` directory
- [ ] T074 [US4] Replace ad-hoc test data with Faker through the shared base in `backend/src/apps/utils/testing.py`
- [ ] T075 [US4] Run `python manage.py test` from `backend/src/` and resolve failures
- [ ] T076 [US4] Build the root `Dockerfile` and verify the image starts Gunicorn over WSGI
- [ ] T077 [US4] Verify no secrets, OTPs, tokens, or production data are committed in `backend/src/` and the repository root

**Checkpoint**: The service is operable, secure, and testable.

---

## Phase 8: User Story 5 - Class-based business logic and backward-compatible services (Priority: P2)

**Goal**: Business logic lives in class-based versioned services and incompatible changes add a new version.

**Independent Test**: Locate each business rule in a service class and verify an incompatible change leaves the old service version intact.

### Tests for User Story 5

- [ ] T078 [P] [US5] Add a test that asserts no business rule lives in a view or loose function in `backend/src/apps/utils/tests/test_service_layer.py`
- [ ] T079 [P] [US5] Add a test that asserts the old service version remains callable after a new version is added in `backend/src/apps/utils/tests/test_service_versioning.py`

### Implementation for User Story 5

- [ ] T080 [US5] Convert loose service functions in `backend/src/apps/accounts/services/v1/accounts.py`, `backend/src/apps/companies/services/v1/companies.py`, `backend/src/apps/catalog/services/v1/catalog.py`, and `backend/src/apps/pipeline/services/v1/pipeline.py` into service classes
- [ ] T081 [US5] Keep the existing public service methods as class methods or wrappers in `backend/src/apps/accounts/services/v1/accounts.py`, `backend/src/apps/companies/services/v1/companies.py`, `backend/src/apps/catalog/services/v1/catalog.py`, and `backend/src/apps/pipeline/services/v1/pipeline.py` so current callers keep working
- [ ] T082 [US5] Move any hard-coded tunable values into `backend/src/config/settings/base.py` or `CONSTANCE_CONFIG`
- [ ] T083 [US5] Run the service-layer and service-versioning tests in `backend/src/apps/utils/tests/test_service_layer.py` and `backend/src/apps/utils/tests/test_service_versioning.py`

**Checkpoint**: Business logic is class-based and versioned.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, final validation, and gate review.

- [ ] T084 [P] Update `backend-rules.md` with the pipeline application convention and the admin-console boundary
- [ ] T085 [P] Update `AGENTS.md` with the pipeline and admin-console module ownership
- [ ] T086 [P] Update `README.md` with the new test command and Dockerfile location
- [ ] T087 Run the [quickstart.md](./quickstart.md) validation scenarios
- [ ] T088 Run the full backend test suite and `python manage.py check` from `backend/src/`
- [ ] T089 Run `python manage.py makemigrations --check --dry-run` from `backend/src/` and confirm no pending changes
- [ ] T090 Review the [contracts/api-conventions.md](./contracts/api-conventions.md) checklist and confirm every gate passes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup; blocks all user stories.
- **US1 (Phase 3)**: Depends on Foundational.
- **US6 (Phase 4)**: Depends on Foundational and US1; it is the structural move that unblocks the API and data work.
- **US2 (Phase 5)**: Depends on US6 because the admin console views import the pipeline interface.
- **US3 (Phase 6)**: Depends on US6 because the moved models need the shared base and audit registration.
- **US4 (Phase 7)**: Depends on US2 and US3.
- **US5 (Phase 8)**: Depends on US2 and US3.
- **Polish (Phase 9)**: Depends on all desired stories.

### User Story Dependencies

- **US1**: No story dependencies.
- **US6**: Depends on US1 for the target layout.
- **US2**: Depends on US6 for the pipeline interface.
- **US3**: Depends on US6 for the moved models.
- **US4**: Depends on US2 and US3.
- **US5**: Depends on US2 and US3.

### Within Each User Story

- Tests before implementation where the test can be written first.
- Models before services.
- Services before viewsets.
- Viewset and serializer work before URL routing.
- Run the story's tests before moving to the next story.

### Parallel Opportunities

- Setup tasks T002–T008 can run in parallel.
- Foundational tasks T011–T015 can run in parallel.
- US1 tests T017–T018 can run in parallel.
- US6 tests T026–T028 can run in parallel.
- US2 tests T042–T044 can run in parallel.
- US3 tests T056–T058 can run in parallel.
- US4 tests T065–T067 can run in parallel.
- US5 tests T078–T079 can run in parallel.

---

## Parallel Example: User Story 6

```bash
# Launch the module-boundary tests together:
Task: "Add pipeline ownership test in backend/src/apps/pipeline/tests/test_module_boundaries.py"
Task: "Add admin-console boundary test in backend/src/apps/admin_console/tests/test_module_boundaries.py"
Task: "Add notifications-removal test in backend/src/apps/utils/tests/test_notifications_removed.py"
```

---

## Implementation Strategy

### MVP First

1. Complete Setup and Foundational.
2. Complete US1 (layout).
3. Complete US6 (pipeline split and notification removal).
4. **STOP and VALIDATE**: Run the module-boundary tests and `manage.py check`.

### Incremental Delivery

1. Setup + Foundational → shared base ready.
2. US1 → layout compliant.
3. US6 → pipeline separated and notifications removed.
4. US2 → API boundary compliant.
5. US3 → data lifecycle compliant.
6. US4 + US5 → operations, security, testing, and services compliant.
7. Polish → documentation and final gate review.

---

## Notes

- `[P]` tasks touch different files and can run in parallel.
- `[US#]` labels map each task to a user story for traceability.
- The pipeline move is the highest-risk task because it changes app labels, foreign keys, migrations, and task paths.
- Keep the existing `/api/v1/ops/` paths used by the frontend when converting to a router.
- Do not edit existing migration files; generate new migrations for every schema change.
