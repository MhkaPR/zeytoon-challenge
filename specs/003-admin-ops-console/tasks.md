---

description: "Task list for Admin Console — Company Approval & Site Data Maintenance"
---

# Tasks: Admin Console — Company Approval & Site Data Maintenance

**Input**: Design documents from `/specs/003-admin-ops-console/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ops-console-api.md, contracts/domtrack-integration.md, quickstart.md

**Tests**: Included. The project constitution (Principle VIII) requires an automated test for
every domain behavior, so test tasks are part of each story.

**Organization**: Tasks are grouped by user story so each of the eight pipeline stories can be
implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1..US8)
- All paths are relative to the repository root.

## Path Conventions

Web application (see plan.md): backend at `backend/src/`, frontend at `frontend/`. New backend
modules are created with `python manage.py startapp` (Principle XII). The operator console API
is mounted at `/api/v1/ops/` and its frontend lives at `frontend/app/ops/**` — **not** `/admin`,
which is Django's built-in admin site.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the new modules, wire configuration, and add the new dependencies

- [X] T001 Create the `admin_console` app with `python manage.py startapp admin_console` and register `"admin_console"` in `INSTALLED_APPS` in `backend/src/config/settings.py`
- [X] T002 [P] Create the `notifications` app with `python manage.py startapp notifications` and register `"notifications"` in `INSTALLED_APPS` in `backend/src/config/settings.py`
- [ ] T003 [P] Mount `path("api/v1/ops/", include("admin_console.urls"))` in `backend/src/config/urls.py` (create the placeholder `backend/src/admin_console/urls.py`) and mount the notifications recipient/inbox routes under `api/v1/ops/` from `notifications.urls`
- [X] T004 [P] Add `django-storages` and `boto3` to the backend dependency list (`backend/requirements.txt` or the project's dependency file) for S3-backed artifacts
- [X] T005 [P] Configure artifact storage in `backend/src/config/settings.py`: `STORAGES["default"]` backed by `storages.backends.s3.S3Storage` (S3-compatible default) with `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_ENDPOINT_URL`, `AWS_S3_REGION_NAME`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` read from environment via the existing `env()` helper; keep a commented local-filesystem alternative so a developer selects the backend from settings without code changes (Principle XIII; research R4)
- [X] T006 [P] Configure the Django Tasks framework in `backend/src/config/settings.py`: `TASKS = {"default": {"BACKEND": env("TASKS_BACKEND", "django.tasks.backends.immediate.ImmediateBackend")}}` (Celery is NOT used; research R2)
- [ ] T007 [P] Configure the email backend for alert notifications from environment variables in `backend/src/config/settings.py` (`EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`)
- [X] T008 [P] Declare this feature's runtime constants in `CONSTANCE_CONFIG` in `backend/src/config/settings.py` with defaults per data-model.md / research R16: `REPLAY_PERIOD_HOURS`, `REPLAY_BATCH_SIZE`, `FAILURE_RATE_THRESHOLD`, `FAILURE_RATE_WINDOW_RUNS`, `LABELING_ENABLED` (default `False`), `LABELING_PROVIDER`, `LABELING_MODEL`, `LABELING_LANGUAGE` (default `"fa"`), `LABELING_BATCH_SIZE`, `SITEMAP_FETCH_TIMEOUT_SECONDS`, `SITEMAP_MAX_INDEX_DEPTH`, `LINK_DISCOVERY_MAX_LINKS`, `CLEANING_RULES`, `CLEANING_UNIT_FAMILIES`, `CAPTURE_MODES_ALLOWED`, `PUBLISH_AUTO_THRESHOLD`, `ALERT_RECIPIENT_DEFAULT_EMAILS`
- [ ] T009 [P] Add Handsontable to `frontend/package.json` (`handsontable` + `@handsontable/react-wrapper`) and install with `yarn install` (research R18)
- [X] T010 [P] Create `backend/src/admin_console/tests/__init__.py`, `backend/src/admin_console/migrations/__init__.py`, and `backend/src/notifications/tests/__init__.py` so pytest and migrations discover the new packages

**Checkpoint**: Both modules exist, routing/config/storage/tasks are wired, dependencies are installed.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The models, artifact store, domtrack adapter, interfaces, and shared plumbing that
every user story depends on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Models (all inherit `utils.models.TimestampedModel`)

- [X] T011 [P] Implement the `Site` model in `backend/src/admin_console/models.py`: `company` (OneToOneField → `companies.Company`, **unique** — one site per company, FR-007), `domain` (CharField, indexed), `has_sitemap` (Boolean, default False), `sitemap_url` (URLField, blank), `maintenance_state` (`onboarding`/`active`/`suspended`), `onboarded_at` (null), `last_replay_at` (null)
- [X] T012 [P] Implement the `Link` model in `backend/src/admin_console/models.py`: `site` (FK), `url` (URLField, indexed), `url_hash` (CharField, indexed; unique together with `site` so discovery is idempotent), `source` (`sitemap`/`manual`), `review_state` (`candidate`/`kept`/`removed`), `pipeline_stage` (`review`/`capture`/`extracted`/`mapped`/`cleaned`/`published`/`flagged`/`failed`), `current_trace` (FK → Trace, null), `failure_rate` (Float, default 0), `is_active` (Boolean), `last_replay_at` (null)
- [X] T013 [P] Implement the `CaptureSession` model in `backend/src/admin_console/models.py`: `link` (FK), `operator` (FK → `accounts.User`), `mode` (`interactive`/`fixed_duration`), `state` (`pending`/`recording`/`awaiting_upload`/`stored`/`failed`), `local_path` (blank), `duration_ms` (null), `error` (blank), `trace` (FK → Trace, null); add a constraint allowing only one non-terminal session per link
- [X] T014 [P] Implement the `Trace` model in `backend/src/admin_console/models.py`: `link` (FK), `capture_session` (FK, null), `captured_by` (FK → `accounts.User`, null), `captured_at`, `origin` (`operator_capture`/`replay_recording`), `storage_key` (CharField, **unique**, UUID-based object key), `storage_backend` (CharField, default `"default"`), `byte_size` (PositiveBigInteger), `content_sha256` (CharField, indexed), `is_valid_trace` (Boolean); **no field stores trace content**
- [X] T015 [P] Implement `ExtractedTable`, `ExtractedTableColumn`, and `ExtractedTableRow` in `backend/src/admin_console/models.py`: table keeps `trace` (FK), `link` (FK), `parent` (blank), `score` (Float), `column_count`/`row_count` (PositiveInteger), `meta` (JSONField); column keeps `table` (FK), `column_id`, `label` (blank), `path` (CharField, **indexed** — domtrack's selector), `atype`, `slot` (blank), `coverage` (Float), `row_count`; row keeps `table` (FK), `row_index` (PositiveInteger), `cells` (JSONField of `{column_id: value}`)
- [X] T016 [P] Implement the `SemanticLabel` model in `backend/src/admin_console/models.py`: `table` (FK), `column_id` (blank for table-level labels), `label`, `provider`, `model`, `language`; must remain optional so nothing depends on it (FR-023)
- [X] T017 [P] Implement `ExtractionRecipe` and `RecipeFieldBinding` in `backend/src/admin_console/models.py`: recipe keeps `link` (FK), `plan_type`, `version`, `is_current` (exactly one per link), `is_complete` (Boolean); binding keeps `recipe` (FK), `schema_field_key`, `source_table` (FK), `source_column` (FK), `selector` (snapshot of the column `path`), `formula` (CharField, Excel/spreadsheet-compatible expression), `aggregation` (blank; `row`/`sum`/`min`/`max`/`concat`)
- [X] T018 [P] Implement the `ReplayRun` model in `backend/src/admin_console/models.py`: `link` (FK), `recipe` (FK), `scheduled_for`/`started_at`/`finished_at`, `state` (`scheduled`/`running`/`succeeded`/`failed`), `before_trace` (FK), `after_trace` (FK, null), `diff_summary` (JSONField), `diff_applied` (Boolean), `stats_applied`/`stats_skipped`/`stats_failed` (PositiveInteger), `failures` (JSONField)
- [X] T019 [P] Implement the `FailureAlert` model in `backend/src/admin_console/models.py`: `link` (FK), `state` (`open`/`resolved`), `failure_rate` (Float), `raised_at`/`resolved_at`, `notification_dedup_key` (CharField, indexed); enforce at most one `open` alert per link
- [X] T020 [P] Implement the `LlmCostLedger` model in `backend/src/admin_console/models.py`: `scope` (`global`/provider-model key), `ceiling_amount` (Decimal, null = ceiling not set), `period` (`daily`/`monthly`/`total`), `updated_by` (FK, null), `timestamp` (for spend rows), `amount` (Decimal), `label_run_ref` (FK → Link, null); ceiling is model-backed, never in settings (Principle II)
- [X] T021 [P] Implement the `PublishedRecord` model in **`backend/src/catalog/models.py`** (the `catalog` app owns published plan data — not `admin_console`): `site`/`link`/`trace`/`recipe` as indexed integer ids (opaque references, no cross-app FK), `source` (default `"admin_console"`), `plan_type`, `natural_key` (indexed), `values` (JSONField keyed by `schema_field_key`), `cleaning_exceptions` (JSONField), `is_published` (Boolean), `published_at`/`retired_at` (null); add a uniqueness constraint on (`source`, `site`, `natural_key`) for upserts
- [X] T022 [P] Implement `Notification`, `NotificationRecipient`, and `NotificationDelivery` in **`backend/src/notifications/models.py`** (general-purpose app, not `admin_console`): notification keeps `event_type` (indexed), `severity` (`info`/`warning`/`critical`), `subject`, `body`, `related_object` (opaque `"app.Model:id"` string), `dedup_key` (blank, indexed); delivery keeps `notification` (FK), `recipient` (FK), `channel` (`in_app`/`email`), `state` (`pending`/`sent`/`failed`), `sent_at`/`read_at` (null), `error` (blank); recipient keeps `user` (FK, null), `email` (indexed), `name` (blank), `is_active` (Boolean), `created_by` (FK, null)
- [X] T023 Create and apply migrations for all three apps with `python manage.py makemigrations admin_console notifications catalog` and `python manage.py migrate` (depends on T011..T022)

### Shared infrastructure

- [X] T024 Implement the artifact store in `backend/src/admin_console/artifacts.py` on top of Django's `STORAGES` API: `save_trace(file) -> (storage_key, byte_size, sha256)` writing under a **UUID-based key** (`traces/<uuid4>.json`) to the configured backend, `open_trace(storage_key)`, `materialize(storage_key) -> temp local path` (for domtrack's path-based API), and `delete_trace(storage_key)`; no hand-written S3 code (Principle XII), no DB blobs (FR-000a)
- [X] T025 [P] Define the code plan schema in `backend/src/admin_console/plan_schema.py`: `PLAN_SCHEMA` with a plan-type dimension (`hosting`, `cdn`, `virtual_server`) and per type an ordered field list of `{key, label, type (number/text/bool/unit/enum), required, unit_family, enum_values}` exactly as in data-model.md; expose `fields_for(plan_type)` and `required_fields(plan_type)`; read-only, never user-editable (FR-027)
- [X] T026 [P] Implement the Excel-compatible formula engine in `backend/src/admin_console/formulas.py`: a tokenizer/validator for spreadsheet syntax (cell/column references, `+ - * / ^`, `=`, parentheses, `&`, and the whitelisted functions `SUM`, `MIN`, `MAX`, `AVERAGE`, `IF`, `ROUND`, `VALUE`, `SUBSTITUTE`, `TEXT`, `CONCATENATE` with `,` argument separator), `validate_formula(expr) -> errors`, and a deterministic `evaluate(expr, cells) -> value`; no `eval`, no arbitrary code (FR-028, research R10)
- [X] T027 Implement the domtrack adapter in `backend/src/admin_console/domtrack_client.py` — the **only** module in the backend that imports `domtrack` (FR-000, SC-017): `start_local_capture(url, mode, duration_ms=None)` (HTTP `POST /capture` on `DOMTRACK_LOCAL_API_URL`), `load_trace(path)`, `is_trace(raw)`, `extract_tables(path, min_rows, min_cols)`, `label_tables(tables, label_config)`, `compare_replay(before_path, replay_config, recording)`, `diff_traces(before_path, after_path)`, `rebuild_dom(path, at_record)`; returns domtrack's own results unmodified (contract: domtrack-integration.md)
- [ ] T028 Define `AdminConsoleInterface` in `backend/src/admin_console/interfaces.py` (the only sanctioned entry point for other modules, Principle V): reads the catalog/search feature needs (published-record source ids, link/site summaries) and no leaked internals
- [X] T029 Define `CatalogInterface` in `backend/src/catalog/interfaces.py` with `upsert_published_record(source, site_id, link_id, trace_id, recipe_id, plan_type, natural_key, values, cleaning_exceptions) -> PublishedRecord` and `retire_published_record(source, site_id, natural_key)`; `catalog` never imports `admin_console` (Principle V, FR-034..FR-036)
- [ ] T030 Implement `backend/src/notifications/interfaces.py` (`notify(event_type, severity, subject, body, related_object="", dedup_key="", recipients=None)`) and `backend/src/notifications/channels.py` (an in-app channel and an email channel through Django's email backend, dispatched from a `django.tasks` task); callers never write notification tables directly (FR-041, research R15)
- [X] T031 [P] Implement structured, masked pipeline events in `backend/src/admin_console/events.py` reusing `utils.logging` (`SensitiveDataFilter`/masking) for every pipeline transition, so no log entry carries unmasked personal data (FR-044, SC-018)
- [X] T032 Implement the operator API base in `backend/src/admin_console/api.py`: an `OperatorOnlyView` (mirroring the `companies` pattern) that resolves the caller via `accounts.selectors.user_from_request`, requires `user.is_admin()`, and returns `403 {"error": {"code": "admin_required", ...}}` plus a shared error-shape helper matching `accounts.exceptions.ApiError` (FR-005, XI)
- [X] T033 [P] Add constance readers in `backend/src/admin_console/constants.py` (`replay_period_hours()`, `failure_rate_threshold()`, `failure_rate_window_runs()`, `labeling_enabled()`, `labeling_config()`, `cleaning_rules()`, `capture_modes_allowed()`, and the rest) so no business-logic module reads constance directly (FR-043, SC-015)
- [X] T034 [P] Implement the LLM ceiling rule in `backend/src/admin_console/services.py`: `llm_ceiling_status(scope, period)` (projection over `LlmCostLedger` spend rows) and `record_llm_cost(...)`, raising a ceiling breach through `notifications` when the ceiling is passed (Principle II, FR-024)
- [ ] T035 [P] Scaffold `backend/src/admin_console/tasks.py` with module-level `django.tasks` task functions (`run_extraction_task`, `run_labeling_task`, `run_replay_task`) that validate their arguments and delegate to services, and create the management command skeleton `backend/src/admin_console/management/commands/run_scheduled_replays.py` (due-run scan → enqueue per-link tasks)
- [ ] T036 Register the new models in `backend/src/admin_console/admin.py` and `backend/src/notifications/admin.py` for operator-side reads (labeling toggle, cost ceiling, recipients) (FR-021, Principle II)

**Checkpoint**: Models, migrations, artifact store, domtrack adapter, plan schema, formula engine, interfaces, notifications core, and shared API plumbing exist — every user story can now begin.

---

## Phase 3: User Story 1 - Company approval (Priority: P1) 🎯 MVP

**Goal**: The operator sees the pending companies with the information needed to decide and
records exactly one append-only outcome per company; an owner can never influence it.

**Independent Test**: With a pending company, record an approval and confirm verified + panel reachable + one decision record + a `Site` created; record a not-approved outcome and confirm the company stays unverified, step one reopens, and the site is suspended; attempt the decision as the owner and get `403`.

### Tests for User Story 1 ⚠️

> Write these FIRST and confirm they FAIL before implementation.

- [X] T037 [P] [US1] Contract test for `GET /api/v1/ops/approvals` and `POST /api/v1/ops/companies/{id}/verification-decisions` in `backend/src/admin_console/tests/test_approval_queue.py`: queue includes name/representative/domain/masked phone and a `duplicate_domain_warning`, 201 on approved ⇒ verified + `Site` in `onboarding`, not_approved ⇒ unverified + step one reopened + `Site` suspended (FR-001, FR-003, FR-004, SC-002, SC-003)
- [X] T038 [P] [US1] Operator-only and append-only test in `backend/src/admin_console/tests/test_approval_authorization.py`: an owner JWT gets `403 admin_required` and changes nothing; a second decision leaves the first `companies.VerificationDecision` row unchanged and both remain readable (FR-005, FR-006, SC-001, SC-004)

### Implementation for User Story 1

- [X] T039 [US1] Add console serializers (Pydantic boundary schemas + DRF I/O) for the approval queue entry and the decision payload (`outcome` ∈ {`approved`, `not_approved`}, `note`) in `backend/src/admin_console/serializers.py` (FR-002)
- [X] T040 [US1] Add console selectors in `backend/src/admin_console/selectors.py`: `pending_approval_queue()` (companies from `CompaniesInterface` awaiting verification, joining the normalized domain to flag duplicates) and `site_for_company(company_id)` (FR-001, FR-004)
- [X] T041 [US1] Implement approval services in `backend/src/admin_console/services.py`: `approve_or_reject_company(company_id, actor, outcome, note)` delegating to `CompaniesInterface.record_verification_decision`, then creating the `Site` in `onboarding` on approval or setting `maintenance_state=suspended` on rejection (FR-003, FR-007, research R20)
- [X] T042 [US1] Implement `ApprovalQueueView` (`GET`) and `VerificationDecisionView` (`POST`) in `backend/src/admin_console/api.py` on the `OperatorOnlyView` base (FR-001, FR-002, FR-005)
- [X] T043 [US1] Wire the approval routes in `backend/src/admin_console/urls.py` (`approvals`, `companies/<int:company_id>/verification-decisions`)
- [X] T044 [US1] Emit structured approval events (decision recorded, site lifecycle started/suspended) in `backend/src/admin_console/events.py` with the phone masked (FR-044, SC-018)
- [ ] T045 [P] [US1] Add the console API client in `frontend/src/lib/api/ops.ts` (typed fetch helpers following the `frontend/src/lib/api/companies.ts` error/CSRF pattern) with the approvals and decision calls (US2..US8 extend this file)
- [ ] T046 [US1] Build the operator shell and role guard in `frontend/app/ops/layout.tsx` (operator-only; non-operators are redirected) and the approvals queue page in `frontend/app/ops/page.tsx` plus `frontend/src/features/ops/approvals/ApprovalQueue.tsx` / `CompanyReviewCard.tsx` with the duplicate-domain warning shown, never auto-resolving (FR-001, FR-004)
- [ ] T047 [P] [US1] Add Persian/RTL copy for the console shell, approvals queue, and decision form in `frontend/src/lib/i18n/strings.ts`
- [ ] T048 [P] [US1] Add frontend tests for the queue, the duplicate warning display, and the decision form in `frontend/tests/ops-approvals.test.tsx`

**Checkpoint**: User Story 1 works independently — the queue can be cleared and a decision always produces exactly one record.

---

## Phase 4: User Story 2 - Site onboarding and link review (Priority: P2)

**Goal**: Onboard the approved company's single site, auto-discover candidate links from its
sitemap (or accept manual entry), review them, and let only kept links proceed.

**Independent Test**: Onboard a site with a sitemap and confirm candidates are discovered; onboard one without and confirm manual entry works; remove some links in review and confirm only kept links are eligible for capture while removed links stay recorded.

### Tests for User Story 2 ⚠️

- [X] T049 [P] [US2] Contract test for `POST /api/v1/ops/sites`, `.../discover-links`, `.../links`, and `.../links/review` in `backend/src/admin_console/tests/test_site_onboarding.py`: 201 onboarding, 409 for a second site on the same company (FR-007), sitemap discovery stores `source="sitemap"` candidates, no sitemap ⇒ `has_sitemap=false` and `discovered=0` (FR-008, SC-005)
- [X] T050 [P] [US2] Link review test in `backend/src/admin_console/tests/test_link_review.py`: removed links become `review_state="removed"` and are excluded from capture while remaining recorded; kept links are capture-eligible; a review keeping none leaves the site in `onboarding` with `link_not_ready` (FR-009, FR-010, FR-011, SC-006)
- [X] T051 [P] [US2] Discovery unit test in `backend/src/admin_console/tests/test_discovery.py`: robots.txt `Sitemap:` directives are honored, `/sitemap.xml` is the fallback, sitemap indexes are followed to `SITEMAP_MAX_INDEX_DEPTH`, `<loc>` entries are normalized to absolute URLs, the transparent user-agent is sent, and discovery is idempotent on `(site, url_hash)` (FR-008, Principle X)

### Implementation for User Story 2

- [X] T052 [US2] Implement sitemap discovery in `backend/src/admin_console/discovery.py` using only stdlib `xml.etree.ElementTree` + `httpx`: `discover_sitemaps(domain)` (robots.txt then `/sitemap.xml`, index nesting up to `SITEMAP_MAX_INDEX_DEPTH`) and `discover_links(sitemap_url)` (respecting robots.txt, the transparent user-agent with contact URL, and per-domain rate limiting) (research R5, Principle X)
- [X] T053 [US2] Implement onboarding services in `backend/src/admin_console/services.py`: `onboard_site(company_id, actor)` (refuse a second site, record `has_sitemap`/`sitemap_url`), `discover_and_store_links(site, actor)` (upsert candidates by `(site, url_hash)`), `add_links_manually(site, urls, actor)`, and `review_links(site, keep_ids, remove_ids, actor)` (FR-007..FR-011)
- [X] T054 [US2] Implement `SiteCreateView`, `DiscoverLinksView`, `SiteLinksView` (`GET`/`POST`), and `LinkReviewView` in `backend/src/admin_console/api.py` (FR-007..FR-011)
- [X] T055 [US2] Wire the site/link routes in `backend/src/admin_console/urls.py` (`sites`, `sites/<int:site_id>/discover-links`, `sites/<int:site_id>/links`, `sites/<int:site_id>/links/review`)
- [X] T056 [US2] Emit structured events for site onboarded, links discovered/entered/removed in `backend/src/admin_console/events.py` (FR-044)
- [ ] T057 [US2] Extend `frontend/src/lib/api/ops.ts` with the site onboarding, discovery, manual-entry, and review calls
- [ ] T058 [US2] Build the site detail page (`frontend/app/ops/sites/[siteId]/page.tsx`, with `frontend/src/features/ops/sites/SiteOnboarding.tsx`) and the link review page (`frontend/app/ops/sites/[siteId]/links/page.tsx`, with `frontend/src/features/ops/links/LinkReviewTable.tsx`) supporting keep/remove (FR-008, FR-009)
- [ ] T059 [P] [US2] Add Persian/RTL copy for onboarding and link review in `frontend/src/lib/i18n/strings.ts`
- [ ] T060 [P] [US2] Add frontend tests for onboarding (sitemap and manual paths) and link review submission in `frontend/tests/ops-links.test.tsx`

**Checkpoint**: User Stories 1 and 2 both work independently.

---

## Phase 5: User Story 3 - Operator-driven capture (Priority: P3)

**Goal**: Trigger **domtrack capture** on the operator's machine for a kept link, open Chrome,
record interactively, then store the resulting trace on the platform (automatic transfer, else
manual upload) before the link can advance.

**Independent Test**: With the local domtrack API running, trigger capture and confirm a session records and reports a trace path; store the trace and confirm a `Trace` row with a UUID `storage_key`; stop domtrack and confirm `502 domtrack_unreachable` with no advance; attempt extraction without a trace and get `409 trace_required`.

### Tests for User Story 3 ⚠️

- [X] T061 [P] [US3] Contract test for `POST /api/v1/ops/links/{id}/captures`, `.../captures/{id}/trace`, and `.../captures/{id}/fail` in `backend/src/admin_console/tests/test_capture_flow.py`: 201 recording for a kept link, 400 for a non-kept link, 502 `domtrack_unreachable` when the local API is down (link not advanced), 201 storing a trace with link/operator/capture-time and `is_valid_trace=true` (FR-012..FR-017, SC-007)
- [X] T062 [P] [US3] Capture session state-machine test in `backend/src/admin_console/tests/test_capture_state.py`: the link cannot pass `capture` while `current_trace` is null, `awaiting_upload` is distinguishable from `failed`, and only one non-terminal session per link exists (FR-014)
- [X] T063 [P] [US3] Artifact storage test in `backend/src/admin_console/tests/test_artifact_storage.py`: `save_trace` writes through the configured `STORAGES` backend under a unique UUID key, `open_trace`/`materialize` round-trip the bytes, `delete_trace` removes the object, and no `Trace` column holds the body (FR-000a, research R4)

### Implementation for User Story 3

- [X] T064 [US3] Implement capture services in `backend/src/admin_console/services.py`: `start_capture(link, operator, mode, duration_ms)` (refuse a non-kept link, call `domtrack_client.start_local_capture`, create the `CaptureSession` as `recording`, map local-service errors to `domtrack_unreachable`), `store_trace(capture_session, file_or_path, operator)` (validate with `domtrack_client.is_trace`, write via `artifacts.save_trace`, create the `Trace`, advance the link), and `fail_capture(capture_session, error)` (FR-012..FR-017)
- [X] T065 [US3] Implement `CaptureStartView`, `TraceUploadView` (multipart file or `local_path`), and `CaptureFailView` in `backend/src/admin_console/api.py` (FR-012, FR-015, FR-017)
- [X] T066 [US3] Wire the capture routes in `backend/src/admin_console/urls.py` (`links/<int:link_id>/captures`, `captures/<int:capture_session_id>/trace`, `captures/<int:capture_session_id>/fail`)
- [X] T067 [US3] Emit structured events for capture started/succeeded/failed and trace stored (with size + hash, never the trace content) in `backend/src/admin_console/events.py` (FR-044, SC-018)
- [ ] T068 [US3] Extend `frontend/src/lib/api/ops.ts` with the capture start, trace upload (multipart), and capture-fail calls
- [ ] T069 [US3] Build the capture page in `frontend/app/ops/links/[linkId]/capture/page.tsx` with `frontend/src/features/ops/capture/CapturePanel.tsx`: the capture button with the interactive/fixed-duration choice, domtrack-unreachable messaging, automatic-transfer attempt with an operator-confirmed manual-upload fallback, and the stage indicator that blocks progression without a stored trace (FR-012..FR-017)
- [ ] T070 [P] [US3] Add Persian/RTL copy for the capture flow in `frontend/src/lib/i18n/strings.ts`
- [ ] T071 [P] [US3] Add frontend tests for the capture panel: mode selection, unreachable error, manual-upload fallback, and blocked advance in `frontend/tests/ops-capture.test.tsx`

**Checkpoint**: User Stories 1–3 work independently.

---

## Phase 6: User Story 4 - Table extraction (Priority: P4)

**Goal**: Convert the stored trace into table documents by invoking **domtrack's discovery**,
and persist them linked to the link and trace; extraction is deterministic and an empty result
flags the link.

**Independent Test**: Extract from a stored trace and confirm tables/columns/rows persist with domtrack's `path` and `coverage`; re-run and confirm identical rows; extract from a trace with no tabular structure and confirm `table_count=0` with the link flagged.

### Tests for User Story 4 ⚠️

- [X] T072 [P] [US4] Contract test for `POST /api/v1/ops/links/{id}/extractions` and `GET .../tables` in `backend/src/admin_console/tests/test_extraction.py`: 201 with tables persisted and `pipeline_stage="extracted"`, each column carrying domtrack's `path`/`atype`/`coverage`; 409 `trace_required` with no stored trace; 200 with `table_count=0` and `pipeline_stage="flagged"` (FR-018, FR-020, SC-007)
- [X] T073 [P] [US4] Determinism test in `backend/src/admin_console/tests/test_extraction_determinism.py`: extracting the same trace twice replaces the previous extraction and yields identical table/column/row rows (FR-019, SC-008)

### Implementation for User Story 4

- [X] T074 [US4] Implement `extract_tables_for_link(link, actor)` in `backend/src/admin_console/services.py`: materialize the stored trace with `artifacts.materialize`, call `domtrack_client.extract_tables` with the constance `min_rows`/`min_cols`/`dedupe` values, persist tables/columns/rows inside a transaction (replacing any previous extraction for that trace), set `pipeline_stage="extracted"`, and flag the link when domtrack returns zero tables (FR-018..FR-020)
- [X] T075 [US4] Implement the `run_extraction_task` body in `backend/src/admin_console/tasks.py` (module-level task calling the service) and have `ExtractionView` enqueue it, returning the result synchronously under the immediate backend (FR-019)
- [X] T076 [US4] Implement `ExtractionView` (`POST`) and `LinkTablesView` (`GET`, tables + columns + rows for the workspace) in `backend/src/admin_console/api.py` (FR-018, FR-025)
- [X] T077 [US4] Wire the extraction routes in `backend/src/admin_console/urls.py` (`links/<int:link_id>/extractions`, `links/<int:link_id>/tables`)
- [X] T078 [US4] Emit structured events for extraction completed/empty in `backend/src/admin_console/events.py`, using aggregation rather than per-row logging (FR-044, Principle VII anti-noise)
- [ ] T079 [US4] Extend `frontend/src/lib/api/ops.ts` with the extraction run and tables-fetch calls
- [ ] T080 [US4] Build the tables page in `frontend/app/ops/links/[linkId]/tables/page.tsx` with `frontend/src/features/ops/tables/TableList.tsx` (candidate tables with score, columns with their `path`, and the flagged state when zero tables were found) (FR-018, FR-020)
- [ ] T081 [P] [US4] Add Persian/RTL copy for the tables view in `frontend/src/lib/i18n/strings.ts`
- [ ] T082 [P] [US4] Add frontend tests for the tables list and the zero-table flagged state in `frontend/tests/ops-tables.test.tsx`

**Checkpoint**: User Stories 1–4 work independently.

---

## Phase 7: User Story 5 - Optional LLM labeling (Priority: P5)

**Goal**: Admin-gated, off-by-default table/column labeling through **domtrack's labeling** on
the server, respecting the model-backed LLM cost ceiling, and never gating another stage.

**Independent Test**: With labeling disabled get `403 labeling_disabled` and confirm the pipeline still works; enable it and confirm meaningful labels persist; lower the ceiling and confirm `409 llm_ceiling_exceeded` with no labels written.

### Tests for User Story 5 ⚠️

- [X] T083 [P] [US5] Gating test in `backend/src/admin_console/tests/test_labeling_gate.py`: labeling is disabled by default (403), enabling it as an admin applies labels via `domtrack_client.label_tables` storing `SemanticLabel` rows, and extraction/mapping/cleaning/publishing/replay behave identically with and without labels (FR-021..FR-023, SC-016)
- [X] T084 [P] [US5] LLM ceiling test in `backend/src/admin_console/tests/test_llm_ceiling.py`: a labeling call that would exceed `ceiling_amount` for the period stops with `409 llm_ceiling_exceeded`, writes no `SemanticLabel` rows, appends no spend row, and raises a ceiling-breach notification (Principle II, FR-024)

### Implementation for User Story 5

- [X] T085 [US5] Implement `label_tables_for_link(link, actor)` in `backend/src/admin_console/services.py`: refuse when `constants.labeling_enabled()` is false, pre-check `llm_ceiling_status`, call `domtrack_client.label_tables` with `constants.labeling_config()` (provider/model/language/batch size; API key from environment only), upsert `SemanticLabel` rows, and call `record_llm_cost` after the call (FR-021, FR-022, FR-024)
- [X] T086 [US5] Implement the `run_labeling_task` body in `backend/src/admin_console/tasks.py` and `LabelingView` (`POST`) in `backend/src/admin_console/api.py`, returning `labeling_disabled` / `llm_ceiling_exceeded` error codes as per the contract (FR-021, FR-024)
- [X] T087 [US5] Wire the labeling route in `backend/src/admin_console/urls.py` (`links/<int:link_id>/labeling`) and add the settings + cost-ceiling endpoints `SettingsView` (`GET`/`PUT`) and `LlmCostCeilingView` (`GET`/`PUT`) in `backend/src/admin_console/api.py` (FR-043, research R16)
- [X] T088 [US5] Emit structured events for labeling run/skipped/ceiling-blocked with call count and cost in `backend/src/admin_console/events.py` (FR-044, Principle VII)
- [ ] T089 [US5] Extend `frontend/src/lib/api/ops.ts` with the labeling call and the settings/cost-ceiling calls
- [ ] T090 [US5] Add the labeling action to `frontend/src/features/ops/tables/TableList.tsx` (showing labels when present and an admin-only enable prompt when disabled) and build the settings page `frontend/app/ops/settings/page.tsx` with `frontend/src/features/ops/settings/TunablesForm.tsx` and `LlmCeilingForm.tsx` (FR-021, FR-043, SC-015)
- [ ] T091 [P] [US5] Add Persian/RTL copy for labeling and settings in `frontend/src/lib/i18n/strings.ts`
- [ ] T092 [P] [US5] Add frontend tests for the labeling toggle, the disabled state, and the tunables form in `frontend/tests/ops-settings.test.tsx`

**Checkpoint**: User Stories 1–5 work independently.

---

## Phase 8: User Story 6 - Merge and mapping to the plan schema (Priority: P6)

**Goal**: A Handsontable workspace where the operator merges tables and connects each schema
field to a source selector plus an Excel-compatible combination formula, producing the durable
extraction recipe.

**Independent Test**: Open the workspace, switch tables with the dropdown, combine fields across tables, connect every required field and save; confirm the recipe records a selector and a spreadsheet-valid formula per field; save with a required field unconnected and get `409 recipe_incomplete`; reopen and confirm the mapping is restored.

### Tests for User Story 6 ⚠️

- [X] T093 [P] [US6] Contract test for `GET /api/v1/ops/plan-schema`, `GET|PUT /api/v1/ops/links/{id}/recipe` in `backend/src/admin_console/tests/test_mapping_recipe.py`: a 200 save records selector + formula per bound field and sets `pipeline_stage="mapped"`, 409 `recipe_incomplete` while a required field is unconnected (link not mapped), 400 for an invalid formula or unknown field/column, and `GET` restores the saved bindings (FR-025..FR-031, SC-009)
- [X] T094 [P] [US6] Excel-compatibility unit test in `backend/src/admin_console/tests/test_formula_excel_compat.py`: valid spreadsheet expressions (`=SUM(A2:A9)`, `=IF(B2>0,B2,0)`, `=ROUND(VALUE(SUBSTITUTE(C2,",","")),0)`) validate and evaluate deterministically, while non-spreadsheet constructs, unknown functions, and any `eval`-style input are rejected (FR-028, research R10)
- [X] T095 [P] [US6] Plan-schema test in `backend/src/admin_console/tests/test_plan_schema.py`: the schema is code-defined and read-only, carries the plan-type dimension (hosting/cdn/virtual_server), and `required_fields(plan_type)` matches the required flags used by the completeness gate (FR-027, FR-030)

### Implementation for User Story 6

- [X] T096 [US6] Implement recipe services in `backend/src/admin_console/services.py`: `save_recipe(link, plan_type, bindings, actor)` validating every binding's field against `plan_schema`, formula against `formulas.validate_formula`, and source column against the link's extracted tables, computing `is_complete` from `required_fields(plan_type)`, versioning the recipe with exactly one `is_current`, and setting `pipeline_stage="mapped"` only when complete (FR-028, FR-030); `get_current_recipe(link)` for restore (FR-031)
- [X] T097 [US6] Implement `PlanSchemaView` (`GET`), `RecipeView` (`GET`/`PUT`), and `LinkTablesView` reuse for the workspace in `backend/src/admin_console/api.py` (FR-025, FR-027, FR-031)
- [X] T098 [US6] Wire the mapping routes in `backend/src/admin_console/urls.py` (`plan-schema`, `links/<int:link_id>/recipe`)
- [X] T099 [US6] Emit structured events for recipe saved and link mapped in `backend/src/admin_console/events.py` (FR-044)
- [ ] T100 [US6] Extend `frontend/src/lib/api/ops.ts` with the plan-schema, recipe-fetch, and recipe-save calls
- [ ] T101 [US6] Build the Handsontable mapping workspace in `frontend/app/ops/links/[linkId]/mapping/page.tsx` and `frontend/src/features/ops/mapping/MappingWorkspace.tsx` (+ `TableSwitcher.tsx`, `FieldBindingPanel.tsx`): the grid renders the selected table, the dropdown switches tables, cross-table combination is supported, formulas are spreadsheet-style, required-field completeness is shown, and a reopened workspace restores saved selectors/formulas (FR-025..FR-031)
- [ ] T102 [P] [US6] Add Persian/RTL copy for the mapping workspace in `frontend/src/lib/i18n/strings.ts`
- [ ] T103 [P] [US6] Add frontend tests for the workspace: table switching, cross-table merge, incomplete-required-field blocking, and restore-on-reopen in `frontend/tests/ops-mapping.test.tsx`

**Checkpoint**: User Stories 1–6 work independently.

---

## Phase 9: User Story 7 - Cleaning and publishing (Priority: P7)

**Goal**: Standardize mapped data so filters can be applied (automatic first, exceptions
surfaced), then publish through the `catalog` interface with full provenance.

**Independent Test**: Clean mapped data with inconsistent units and confirm standardization with only exceptions returned; publish and confirm records in `catalog` with site/link/trace/recipe provenance; confirm an unconnected required field blocks publishing.

### Tests for User Story 7 ⚠️

- [X] T104 [P] [US7] Cleaning test in `backend/src/admin_console/tests/test_cleaning.py`: unit/number/range/category rules standardize values so filters apply, automatically cleanable data needs no operator action, only unresolvable exceptions are surfaced, a record with an exception keeps its other cleaned fields and stays publishable, and rule values come from constance (FR-032, FR-033, FR-043, SC-011)
- [X] T105 [P] [US7] Publishing test in `backend/src/admin_console/tests/test_publishing.py`: publishing writes `catalog.PublishedRecord` rows **through `CatalogInterface`** with site/link/trace/recipe provenance and upserts by `(source, site, natural_key)`; a replay-reported removal retires the record rather than leaving stale values; publishing is refused with `409 recipe_incomplete` when a required field is unconnected; `catalog` never imports `admin_console` (FR-030, FR-034..FR-036, SC-009)

### Implementation for User Story 7

- [X] T106 [US7] Implement the cleaning rules engine in `backend/src/admin_console/cleaning.py`: a registry keyed by field/unit family driven by the constance `CLEANING_RULES` / `CLEANING_UNIT_FAMILIES` values (unit standardization such as GB/TB↔numeric and Mbps/Gbps, number and range parsing, currency separators, enum/category normalization via the plan schema's `enum_values`) returning `(cleaned_value, outcome)` per value (FR-032, FR-033)
- [X] T107 [US7] Implement `clean_link_data(link, actor)` in `backend/src/admin_console/services.py`: evaluate the link's current recipe with `formulas.evaluate` over the extracted rows (no operator re-mapping, FR-029), run every value through the cleaning engine, collect exceptions, set `pipeline_stage="cleaned"` (FR-032, FR-033)
- [X] T108 [US7] Implement `publish_link_data(link, actor)` in `backend/src/admin_console/services.py`: refuse unless the current recipe `is_complete`, then call `CatalogInterface.upsert_published_record` per item and set `pipeline_stage="published"`; `replay.py` removal handling calls `CatalogInterface.retire_published_record` (FR-030, FR-034..FR-036)
- [X] T109 [US7] Implement `CleaningView` (`POST`) and `PublishView` (`POST`) in `backend/src/admin_console/api.py` and wire them in `backend/src/admin_console/urls.py` (`links/<int:link_id>/cleaning`, `links/<int:link_id>/publish`)
- [X] T110 [US7] Emit structured events for cleaning completed/exception and published/removed in `backend/src/admin_console/events.py`, aggregated rather than per row (FR-044, Principle VII anti-noise)
- [ ] T111 [US7] Extend `frontend/src/lib/api/ops.ts` with the cleaning and publish calls
- [ ] T112 [US7] Build the cleaning/publish page in `frontend/app/ops/links/[linkId]/publish/page.tsx` with `frontend/src/features/ops/publishing/CleaningPanel.tsx` (exception list with resolution, publish action, provenance summary) and the stage indicator in `frontend/src/features/ops/pipeline/StageBadge.tsx` (FR-033, FR-035)
- [ ] T113 [P] [US7] Add Persian/RTL copy for cleaning/publishing in `frontend/src/lib/i18n/strings.ts`
- [ ] T114 [P] [US7] Add frontend tests for cleaning exceptions and the publish flow in `frontend/tests/ops-publishing.test.tsx`

**Checkpoint**: User Stories 1–7 work independently.

---

## Phase 10: User Story 8 - Scheduled replay, diff, and failure alerting (Priority: P8)

**Goal**: Replay maintained links on a configured period with **domtrack replay + compare/diff**,
apply differences to published data, track a per-link failure rate, and raise naming
notifications through the `notifications` app when the rate crosses the threshold.

**Independent Test**: Configure a short period, run `python manage.py run_scheduled_replays`, and confirm each due link gets a `ReplayRun` with before/after traces and an applied diff; force a failure rate past the threshold and confirm one alert names the link with an in-app notification and an email; re-run the flagged link through all stages and see it return to active.

### Tests for User Story 8 ⚠️

- [ ] T115 [P] [US8] Contract test for `GET|POST /api/v1/ops/replay-runs`, `GET .../links/{id}/failure`, and `GET .../alerts` in `backend/src/admin_console/tests/test_replay_diff.py`: due links are replayed, each run records before/after traces, a diff summary, `diff_applied=true`, and domtrack stats; the diff is applied to published data and a removal retires the record (FR-037..FR-039, SC-012)
- [ ] T116 [P] [US8] Scheduler test in `backend/src/admin_console/tests/test_replay_scheduler.py`: `run_scheduled_replays` selects only links whose `now - last_replay_at >= REPLAY_PERIOD_HOURS` on an `active` site with a complete recipe, skips `suspended` sites, enqueues one `django.tasks` task per link, and uses no Celery broker (FR-037, FR-043, research R2)
- [ ] T117 [P] [US8] Failure-rate and alerting test in `backend/src/admin_console/tests/test_failure_alerts.py`: the failure rate derives from domtrack's reported failures over `FAILURE_RATE_WINDOW_RUNS`, crossing `FAILURE_RATE_THRESHOLD` creates exactly one `open` alert naming the link, the alert is not repeated on subsequent replays while open, and a later re-crossing after resolution creates a new alert (FR-040, SC-013)
- [ ] T118 [P] [US8] Notifications test in `backend/src/admin_console/tests/test_notifications_delivery.py`: each alert produces one `Notification` through `notifications/interfaces.notify` with one `NotificationDelivery` per active recipient per channel (`in_app` and `email`), `dedup_key` prevents duplicates, a failed email is recorded without blocking the in-app delivery, and recipients can be added/deactivated by an admin only (FR-041, research R15)

### Implementation for User Story 8

- [ ] T119 [US8] Implement replay orchestration in `backend/src/admin_console/replay.py`: `execute_replay_run(link)` materializing the before trace, calling `domtrack_client.compare_replay` with the constance `ReplayConfig`/`RecordingConfig` (clean mode + third-party detection), storing the after trace through `artifacts.save_trace`, recording the `ReplayRun` (stats, failures, diff summary), applying the diff to published data via `CatalogInterface` (upserts and retirements), and recomputing `Link.failure_rate` (FR-037..FR-039)
- [ ] T120 [US8] Implement alert raising in `backend/src/admin_console/services.py`: `evaluate_failure_alert(link)` creates/resolves `FailureAlert` state transitionally and, on opening a new alert, calls `notifications.interfaces.notify(event_type="link_failure_rate_exceeded", ..., dedup_key=<alert key>)` (state-based so it is not re-raised every cycle) (FR-040, FR-041)
- [ ] T121 [US8] Complete the `run_scheduled_replays` management command in `backend/src/admin_console/management/commands/run_scheduled_replays.py`: select due links, enqueue `run_replay_task` per link via `django.tasks`, and print a summary; add the `run_replay_task` body in `backend/src/admin_console/tasks.py` (FR-037, research R2)
- [ ] T122 [US8] Implement `ReplayRunListView`/`ReplayRunCreateView`, `LinkFailureView`, `AlertListView`, `LinkRerunView`, and the recipient endpoints (`NotificationRecipientListCreateView`, `NotificationRecipientDeactivateView`) in `backend/src/admin_console/api.py`, and wire them in `backend/src/admin_console/urls.py` (FR-037..FR-042)
- [ ] T123 [US8] Implement `rerun_link_stages(link, actor)` in `backend/src/admin_console/services.py` resetting the link to `capture` with its prior state preserved for audit, so the operator can re-run capture → extract → map → clean → publish and the link returns to `active` (FR-042, SC-014)
- [ ] T124 [US8] Wire the notifications app API in `backend/src/notifications/api.py` + `backend/src/notifications/urls.py` for the in-app inbox and recipient management, mounted under `/api/v1/ops/` (FR-041)
- [ ] T125 [US8] Emit structured events for replay run completed (with failure rate and staleness), alert raised/resolved, and notification delivery in `backend/src/admin_console/events.py` and `backend/src/notifications/events.py` (FR-044, FR-045, Principle VII)
- [ ] T126 [US8] Extend `frontend/src/lib/api/ops.ts` with the replay-run, failure, alert, rerun, and recipient calls
- [ ] T127 [US8] Build the replay & alerts page in `frontend/app/ops/replay/page.tsx` with `frontend/src/features/ops/replay/ReplayRunsTable.tsx` (before/after traces, diff summary, stats), `FailureRateBadge.tsx`, `AlertsPanel.tsx` (with a re-run action), and `RecipientManager.tsx` (FR-040..FR-042)
- [ ] T128 [P] [US8] Add Persian/RTL copy for replay, alerts, and recipients in `frontend/src/lib/i18n/strings.ts`
- [ ] T129 [P] [US8] Add frontend tests for the replay table, the failure badge, the alerts panel re-run action, and recipient management in `frontend/tests/ops-replay.test.tsx`

**Checkpoint**: All eight user stories are independently functional.

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Guarantees that span every story

- [ ] T130 [P] Add the domtrack-reuse guard test in `backend/src/admin_console/tests/test_domtrack_reuse.py` that walks the backend source tree and fails if `domtrack` is imported anywhere except `backend/src/admin_console/domtrack_client.py` (FR-000, SC-017)
- [ ] T131 [P] Add the log-masking test in `backend/src/admin_console/tests/test_log_masking.py` asserting no captured log record contains an unmasked phone number or trace content (FR-044, SC-018)
- [ ] T132 [P] Add the tunables test in `backend/src/admin_console/tests/test_tunables_runtime.py` asserting replay period, failure threshold, labeling toggle, and cleaning rules all take effect after a runtime change through `PUT /api/v1/ops/settings` with no code change (FR-043, SC-015)
- [ ] T133 [P] Add the interface-boundary test in `backend/src/admin_console/tests/test_module_boundaries.py` asserting `catalog` and `notifications` never import `admin_console` and that published records are written only through `CatalogInterface` (Principle V)
- [ ] T134 Add the operations metrics endpoint `MetricsView` (`GET /api/v1/ops/metrics`) in `backend/src/admin_console/api.py` reporting crawl success rate per provider, per-source latency, LLM call count and cost, replay staleness, and open alert count (FR-045, Principle VII)
- [ ] T135 [P] Add the operator console README section documenting `/ops` vs Django `/admin`, the local `domtrack serve` prerequisite and port guidance, and the `STORAGES` S3-vs-local switch in `specs/003-admin-ops-console/quickstart.md` if gaps remain
- [ ] T136 Update `frontend/src/lib/i18n/strings.ts` and the console nav in `frontend/app/ops/layout.tsx` so every console screen is reachable and localized (Persian/RTL), with sample-path logging kept out of business logic
- [ ] T137 Regenerate the OpenAPI schema with `python manage.py spectacular --file /tmp/schema.yml` and confirm the console endpoints appear under `/api/v1/ops/` with the shared error shape (drf-spectacular contract check)
- [ ] T138 Run the full backend suite (`.venv/bin/python -m pytest backend/src/admin_console/tests backend/src/notifications/tests backend/src/catalog/tests backend/src/companies/tests -q`) and the frontend suite (`cd frontend && yarn test`), then fix any regressions introduced by this feature
- [ ] T139 Run the [quickstart.md](./quickstart.md) validation scenarios V1–V8 end-to-end against a local stack (SQLite/Redis, local `domtrack serve`, local `STORAGES` backend) and record the results

**Checkpoint**: The feature is complete, contract-verified, and validated end-to-end.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS all user stories**
- **User Stories (Phases 3–10)**: All depend on Foundational; stories can then proceed in parallel (if staffed) or sequentially P1 → P8
- **Polish (Phase 11)**: Depends on all desired stories being complete

### User Story Dependencies

- **US1 (P1)**: No dependencies on other stories — creates the `Site` that later stories use, and is the MVP
- **US2 (P2)**: Depends on US1 only for an approved company's `Site` (the `Site` model is foundational), so it is independently testable by seeding an approved company
- **US3 (P3)**: Depends on US2 keeping at least one link (`review_state="kept"`); independently testable with a seeded kept link
- **US4 (P4)**: Depends on a stored trace (US3); independently testable with a seeded trace + a fake/injected domtrack result
- **US5 (P5)**: Depends on extracted tables (US4) to have something to label; never blocks US4–US8 (FR-023)
- **US6 (P6)**: Depends on extracted tables (US4); independent of US5 (labels are optional)
- **US7 (P7)**: Depends on a complete recipe (US6); publishes through `catalog` (foundational interface)
- **US8 (P8)**: Depends on a complete recipe and published data (US6, US7); raises alerts through `notifications` (foundational interface)

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models were completed in Foundational; per story: serializers → selectors/services → endpoints → frontend
- Core implementation before frontend integration
- Story complete and independently validated before moving to the next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational model tasks marked [P] can run in parallel (T011–T022), then T023 migrates
- Once Foundational completes, US1–US8 can be staffed in parallel (subject to the story dependencies above)
- Within a story, all test tasks marked [P] run in parallel, and all frontend copy/tests tasks marked [P] run in parallel

---

## Parallel Example: User Story 6

```bash
# Tests first (all independent files):
Task: "Contract test for plan-schema and recipe endpoints in backend/src/admin_console/tests/test_mapping_recipe.py"
Task: "Excel-compatibility unit test in backend/src/admin_console/tests/test_formula_excel_compat.py"
Task: "Plan-schema test in backend/src/admin_console/tests/test_plan_schema.py"

# Then frontend extras in parallel with the workspace build:
Task: "Add Persian/RTL copy for the mapping workspace in frontend/src/lib/i18n/strings.ts"
Task: "Add frontend tests for the workspace in frontend/tests/ops-mapping.test.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (approval queue + decisions)
4. **STOP and VALIDATE**: run `backend/src/admin_console/tests/test_approval_queue.py` and `test_approval_authorization.py`, then exercise V1 from quickstart.md
5. Deploy/demo if ready — operators can clear the verification queue

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → validate (MVP: company approval)
3. US2 → validate (links flowing)
4. US3 → validate (real traces entering the platform)
5. US4 → validate (tables persisted, deterministic)
6. US5 → validate (optional labels, ceiling enforced)
7. US6 → validate (recipe saved and reproducible)
8. US7 → validate (clean, published, provenance intact)
9. US8 → validate (self-refreshing data with alerting)
10. Polish → contract, masking, tunables, and boundary guarantees

### Parallel Team Strategy

With multiple developers, complete Setup + Foundational together, then assign US1, US2, and
US3 to separate developers (the earliest pipeline stages), moving later stories forward as
their upstream stage lands. US5 can be built in parallel with US4/US6 because labeling never
gates another stage.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps each task to its user story for traceability
- Every task names an exact file path so it is executable without extra context
- No Celery anywhere: background work is `django.tasks` (T006) plus `run_scheduled_replays` (T121)
- domtrack is imported only in `backend/src/admin_console/domtrack_client.py` (T027), locked by T130
- The operator console is `/api/v1/ops/` and `frontend/app/ops/**` — never `/admin` (a Django admin URL)
- Published records live in `catalog` (T021/T029), notifications in `notifications` (T022/T030)
