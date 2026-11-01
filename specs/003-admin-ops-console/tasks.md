---

description: "Task list for Admin Console — Company Approval & Automated Site Data Pipeline"
---

# Tasks: Admin Console — Company Approval & Automated Site Data Pipeline

**Input**: Design documents from `/specs/003-admin-ops-console/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ops-console-api.md, contracts/domtrack-integration.md, quickstart.md

**Tests**: Included. The project constitution (Principle VIII) requires an automated test for
every domain behavior, so test tasks are part of each story.

**Organization**: Tasks are grouped by user story so each of the ten pipeline stories can be
implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1..US10)
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
- [X] T003 [P] Mount `path("api/v1/ops/", include("admin_console.urls"))` in `backend/src/config/urls.py` and mount the notifications recipient/inbox routes under `api/v1/ops/` from `notifications.urls`
- [X] T004 [P] Add `django-storages` and `boto3` to the backend dependency list for S3-backed artifacts
- [X] T005 [P] Add `crawl4ai` to the backend dependency list and install a headless Chromium for the server (domtrack and crawl4ai both drive it) (FR-008, FR-016)
- [X] T006 [P] Configure artifact storage in `backend/src/config/settings.py`: `STORAGES["default"]` backed by `storages.backends.s3.S3Storage` (S3-compatible default) with credentials from `env()`, plus a commented local-filesystem alternative (Principle XIII; research R4)
- [X] T007 [P] Configure the Django Tasks framework in `backend/src/config/settings.py`: `TASKS = {"default": {"BACKEND": env("TASKS_BACKEND", "django.tasks.backends.immediate.ImmediateBackend")}}` (Celery is NOT used; research R2)
- [X] T008 [P] Do not configure email delivery; alerts are in-app only by project decision, so no `EMAIL_*` settings exist
- [X] T009 [P] Declare this feature's runtime constants in `CONSTANCE_CONFIG`: `REPLAY_PERIOD_HOURS`, `REPLAY_BATCH_SIZE`, `FAILURE_RATE_THRESHOLD`, `FAILURE_RATE_WINDOW_RUNS`, `LABELING_ENABLED` (default `False`), `LABELING_PROVIDER`, `LABELING_MODEL`, `LABELING_LANGUAGE` (default `"fa"`), `LINK_CRAWL_QUERY_FA`, `LINK_CRAWL_QUERY_EN`, `LINK_CRAWL_MAX_PAGES`, `LINK_CRAWL_MAX_DEPTH`, `LINK_CRAWL_TOP_K`, `LINK_DENY_EXTENSIONS`, `LINK_DENY_SEGMENTS`, `LINK_DISCOVERY_MAX_LINKS`, `REFILTER_PROVIDER`, `REFILTER_MODEL`, `REFILTER_DROP_CONFIDENCE`, `CAPTURE_FIXED_DURATION_MS`, `CAPTURE_NAV_TIMEOUT_MS`, `RETRY_MAX_ATTEMPTS`, `RETRY_BACKOFF_SECONDS`, `PUBLISH_AUTO_THRESHOLD` (FR-054)
- [X] T010 [P] Remove Handsontable from `frontend/package.json`; the mapping workspace is retired (no spreadsheet dependency)
- [X] T011 [P] Create `backend/src/admin_console/tests/__init__.py`, `backend/src/admin_console/migrations/__init__.py`, and `backend/src/notifications/tests/__init__.py`

**Checkpoint**: Both modules exist, routing/config/storage/tasks are wired, dependencies are installed.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The models, artifact store, domtrack/crawl4ai/LLM adapters, interfaces, and shared
plumbing that every user story depends on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Models (all inherit `utils.models.TimestampedModel`)

- [ ] T012 [P] Implement the `Site` model: `company` (OneToOneField → `companies.Company`, **unique**, FR-007), `domain` (indexed; crawl seed), `crawl_query` (blank), `maintenance_state` (`onboarding`/`active`/`suspended`), `onboarded_at` (null), `last_replay_at` (null); **no sitemap fields**
- [ ] T013 [P] Implement the `Link` model: `site` (FK), `url`/`url_hash` (unique together with `site`), `source` (`adaptive_crawl`/`manual`), `review_state` (`candidate`/`kept`/`dropped`/`flagged`), `refilter_plan_type` (blank)/`refilter_confidence` (null)/`refilter_flag` (Boolean), `pipeline_stage` (`discovered`→`refiltered`→`captured`→`extracted`→`classified`→`plans_extracted`→`published`; plus `awaiting_llm_budget`/`flagged`/`dead_lettered`), `current_trace` (FK, null), `failure_rate` (Float), `retry_count` (PositiveInteger, default 0), `last_error` (blank), `is_active` (Boolean), `last_replay_at` (null) (FR-009..FR-015, FR-018, FR-052)
- [ ] T014 [P] Implement the `CaptureSession` model: `link` (FK), `mode` (`headless_fixed` only), `state` (`pending`/`recording`/`stored`/`failed`), `duration_ms` (PositiveInteger), `error` (blank), `trace` (FK, null); only one non-terminal session per link; **no operator/local-path fields** (FR-016..FR-018)
- [ ] T015 [P] Implement the `Trace` model: `link` (FK), `capture_session` (FK, null), `captured_at`, `origin` (`server_capture`/`replay_recording`), `storage_key` (unique, UUID-based), `storage_backend` (default `"default"`), `byte_size`, `content_sha256` (indexed), `is_valid_trace`; **no trace content column**; no `captured_by` (FR-019, FR-053)
- [ ] T016 [P] Implement `ExtractedTable`, `ExtractedTableColumn`, `ExtractedTableRow`: table keeps `trace`/`link` (FK), `parent`, `score`, `column_count`/`row_count`, `meta`; column keeps `column_id`, `label` (blank), `path` (indexed, diagnostics only), `atype`, `slot`, `coverage`, `row_count`; row keeps `row_index`, `cells` (JSON) (FR-020)
- [ ] T017 [P] Implement the `TableClassification` model: `table` (OneToOneField → ExtractedTable), `is_plans_table` (Boolean), `plan_type` (blank), `confidence` (Float), `provider`/`model`/`prompt_version` (CharField) (FR-023..FR-025)
- [ ] T018 [P] Implement the `PlanRecord` model: `link`/`table`/`classification` (FK), `plan_type`, `natural_key` (indexed), `values` (JSON keyed by schema field key), `confidence` (null), `prompt_version` (FR-026..FR-031)
- [ ] T019 [P] Implement the `SemanticLabel` model: `table` (FK), `column_id` (blank for table-level), `label`, `provider`/`model`, `language`; optional, nothing depends on it (FR-032..FR-034)
- [ ] T020 [P] Implement the `ReplayRun` model: `link` (FK), `scheduled_for`/`started_at`/`finished_at`, `state` (`scheduled`/`running`/`succeeded`/`failed`/`awaiting_llm_budget`), `before_trace`/`after_trace` (FK), `diff_summary` (JSON), `reextracted` (Boolean), `stats_applied`/`stats_skipped`/`stats_failed`, `failures` (JSON); **no recipe FK** (FR-039..FR-043)
- [ ] T021 [P] Implement the `ChangeRecord` model: `replay_run` (FK), `change_kind` (`content`/`structural`), `touches_plans_table` (Boolean), `classification` (FK, null), `summary` (JSON) (FR-041, FR-042)
- [ ] T022 [P] Implement the `FailureAlert` model: `link` (FK), `state` (`open`/`resolved`), `failure_rate`, `raised_at`/`resolved_at`, `notification_dedup_key` (indexed); at most one `open` alert per link (FR-044)
- [ ] T023 [P] Implement the `LlmCostLedger` as the **token budget + spend** model: `scope`, `token_budget` (BigInteger, null), `period` (`daily`/`monthly`/`total`), `updated_by` (FK, null), `timestamp`, `tokens_used`, `amount` (null), `stage` (`refilter`/`classification`/`schema_extraction`/`labeling`), `link_ref`/`table_ref` (FK, null), `idempotency_key` (**unique**) (FR-047..FR-050, Principle II)
- [ ] T024 [P] Implement the `PublishedRecord` model in **`backend/src/catalog/models.py`** (the `catalog` app owns published plan data): `site`/`link`/`trace`/`classification` as indexed integer ids (opaque, no cross-app FK), `source` (default `"admin_console"`), `plan_type`, `natural_key` (indexed), `values` (JSON), `is_published` (Boolean), `published_at`/`retired_at` (null); uniqueness on (`source`, `site`, `natural_key`); **no `recipe` id and no `cleaning_exceptions`** (FR-036..FR-038)
- [ ] T025 Generate migrations for `admin_console`, `notifications`, and `catalog` and apply them

### Shared infrastructure

- [ ] T026 [P] Implement the artifact store in `backend/src/admin_console/artifacts.py`: `save_trace(bytes) -> (key, backend, byte_size, sha256)` writing under a UUID-based key (`traces/<uuid4>.json`), `open_trace`, `materialize(storage_key) -> temp path`, and `delete_trace`; write the object before committing the `Trace` row and compensate orphans (FR-053)
- [ ] T027 [P] Define the code plan schema in `backend/src/admin_console/plan_schema.py` as Pydantic models: plan types `hosting`/`cdn`/`virtual_server` with their fields exactly as in data-model.md; expose `schema_for(plan_type)`, `required_fields(plan_type)`; read-only, hand-edited (FR-027)
- [ ] T028 [P] Implement the domtrack adapter in `backend/src/admin_console/domtrack_client.py` — the **only** backend module importing `domtrack` (FR-000, SC-020): `capture_headless(url, duration_ms, nav_timeout_ms)`, `load_trace(path)`, `is_trace(raw)`, `extract_tables(path, min_rows, min_cols)`, `label_tables(tables, label_config)`, `compare_replay(before_path, replay_config, recording)`; returns domtrack results unmodified (contract: domtrack-integration.md)
- [ ] T029 [P] Implement the discovery adapter in `backend/src/admin_console/discovery.py` — the **only** backend module importing `crawl4ai`: `crawl_candidate_links(domain, query, bounds) -> list[str]` using `AdaptiveCrawler(AdaptiveConfig(strategy="statistical", ...))`, plus `apply_link_policy(urls, deny_extensions, deny_segments) -> list[str]` (same-host, fragment/query strip, dedupe) (FR-008, FR-009)
- [ ] T030 [P] Implement the LLM client in `backend/src/admin_console/llm.py`: an OpenAI-compatible client (base URL/key from env, provider `openai` or `compatible`) with `classify_tables(...)`, `extract_plans(...)`, and `refilter_page(...)`, each returning validated Pydantic objects; the single place any LLM call is made (FR-023, FR-026, FR-012)
- [ ] T031 [P] Implement the artifact-storage helpers for the refilter's deterministic extraction in `backend/src/admin_console/refilter.py`: `important_section(html) -> {h1..h3, text}` (largest text-density block in `<main>`/`<article>`, nav/footer/script stripped, capped) — no LLM, no HTML sent downstream (FR-012)
- [ ] T032 Define `AdminConsoleInterface` in `backend/src/admin_console/interfaces.py` as the only sanctioned entry point for other modules (Principle V)
- [ ] T033 Define `CatalogInterface` in `backend/src/catalog/interfaces.py` with `upsert_published_record(source, site_id, link_id, trace_id, classification_id, plan_type, natural_key, values)` and `retire_published_record(source, site_id, natural_key)`; `catalog` never imports `admin_console` (Principle V)
- [ ] T034 Implement `backend/src/notifications/interfaces.py` (`notify(...)`) and `channels.py` (in-app channel dispatched from a `django.tasks` task; email intentionally absent) (FR-045)
- [ ] T035 [P] Implement structured, masked pipeline events in `backend/src/admin_console/events.py` reusing `utils.logging` masking, so no log entry carries unmasked personal data (FR-055, SC-021)
- [ ] T036 Implement the operator API base in `backend/src/admin_console/api.py`: an `OperatorOnlyView` (mirroring the `companies` pattern) requiring `user.is_admin()` and a shared error shape (FR-005)
- [ ] T037 [P] Add constance readers in `backend/src/admin_console/constants.py` for every constant in T009 so no business-logic module reads constance directly (FR-054)
- [ ] T038 [P] Implement the budget gate in `backend/src/admin_console/llm.py`: `budget_allows(stage, scope, period)`, `record_llm_spend(...)` keyed by `idempotency_key`, and `budget_exhausted(stage)` marking a link `awaiting_llm_budget` and raising a `notifications` alert (FR-047..FR-050)
- [ ] T039 [P] Scaffold `backend/src/admin_console/tasks.py` with `django.tasks` task functions (`run_capture_task`, `run_extraction_task`, `run_classification_task` for combined table classification and plan extraction, `run_labeling_task`, `run_replay_task`) and the management command skeleton `backend/src/admin_console/management/commands/run_scheduled_replays.py`
- [ ] T040 Register the new models in `backend/src/admin_console/admin.py` and `backend/src/notifications/admin.py` for operator-side reads (labeling toggle, token budget, recipients)

**Checkpoint**: Models, artifact store, domtrack/crawl4ai/LLM adapters, plan schema, interfaces, budget gate, and shared plumbing exist.

---

## Phase 3: User Story 1 - Company approval (Priority: P1) 🎯 MVP

**Goal**: List pending companies and record exactly one append-only decision, with owner refusal.

**Independent Test**: Approve/deny from the queue and confirm the decision record and the company's verification state; confirm an owner cannot set their own status.

### Tests for User Story 1 ⚠️

- [ ] T041 [P] [US1] Contract test for `GET /api/v1/ops/companies` and `POST /api/v1/ops/companies/{id}/decision` in `backend/src/admin_console/tests/test_approval_queue.py`
- [ ] T042 [P] [US1] Authorization test in `backend/src/admin_console/tests/test_approval_authorization.py` (owner refused; operator-only)

### Implementation for User Story 1

- [ ] T043 [US1] Implement the approval queue + decision services in `backend/src/admin_console/services.py`, delegating verification to `companies/interfaces.py`
- [ ] T044 [US1] Implement `CompanyQueueView`/`DecisionView` in `backend/src/admin_console/api.py` and wire `backend/src/admin_console/urls.py`
- [ ] T045 [P] [US1] Emit masked decision/site-lifecycle events in `backend/src/admin_console/events.py`
- [ ] T046 [P] [US1] Add the console API client in `frontend/src/lib/api/ops.ts` and the operator shell + role guard in `frontend/app/ops/layout.tsx` / `page.tsx`
- [ ] T047 [P] [US1] Add Persian/RTL copy and frontend tests for the queue/decision in `frontend/src/lib/i18n/strings.ts` and `frontend/tests/ops-approvals.test.tsx`

**Checkpoint**: US1 works independently — the queue can be cleared and a decision always produces exactly one record.

---

## Phase 4: User Story 2 - Automated link discovery (crawl4ai) (Priority: P2)

**Goal**: Onboard an approved company's site by adaptive crawling (statistical) and reduce the
harvested links with the deterministic host/extension/segment policy.

**Independent Test**: Onboard a site (stubbed crawler) and confirm a deduplicated candidate set with denied extensions/segments excluded; confirm no sitemap request.

### Tests for User Story 2 ⚠️

- [ ] T048 [P] [US2] Discovery test in `backend/src/admin_console/tests/test_link_discovery.py`: the statistical strategy is used (no embeddings/LLM), unknown extensions/segments are denied, same-host/query-strip/dedupe hold, and no sitemap is fetched (FR-008, FR-009, SC-005, SC-006)
- [ ] T049 [P] [US2] Contract test for `POST /api/v1/ops/sites` and `.../discover-links` in `backend/src/admin_console/tests/test_site_onboarding.py`: 201 onboarding, 409 for a second site, `source="adaptive_crawl"` candidates stored, empty crawl keeps the site in `onboarding` (FR-007, FR-011)

### Implementation for User Story 2

- [ ] T050 [US2] Implement `crawl_candidate_links` / `apply_link_policy` in `backend/src/admin_console/discovery.py` (research R5/C4A)
- [ ] T051 [US2] Implement onboarding/discovery services in `backend/src/admin_console/services.py`: `onboard_site`, `discover_and_store_links` (upsert by `(site, url_hash)`), `add_links_manually` (FR-007..FR-011)
- [ ] T052 [US2] Implement `SiteCreateView`/`DiscoverLinksView`/`SiteLinksView` in `backend/src/admin_console/api.py` and wire routes
- [ ] T053 [P] [US2] Emit masked discovery events in `backend/src/admin_console/events.py`
- [ ] T054 [P] [US2] Build the site detail + discovered-links pages (`frontend/app/ops/sites/[siteId]/**`) and the `ops.ts` calls
- [ ] T055 [P] [US2] Add Persian/RTL copy and frontend tests in `frontend/src/lib/i18n/strings.ts` and `frontend/tests/ops-links.test.tsx`

**Checkpoint**: US1 and US2 both work independently.

---

## Phase 5: User Story 3 - LLM link refilter (Priority: P3)

**Goal**: Deterministically extract `h1–h3` + important section and refilter each candidate with
an LLM before capture, recall-biased.

**Independent Test**: Confirm the model input excludes HTML; a confidently non-plans page is dropped; a borderline page is kept and flagged; budget exhaustion parks the link.

### Tests for User Story 3 ⚠️

- [ ] T056 [P] [US3] Refilter test in `backend/src/admin_console/tests/test_link_refilter.py`: `important_section` returns the largest `<main>`/`<article>` block; the model receives only URL/headings/section; only confidently non-plans links are dropped; borderline keeps are flagged (FR-012..FR-015, SC-007)
- [ ] T057 [P] [US3] Contract test for `POST /api/v1/ops/links/{id}/refilter` and `.../links/{id}/refilter/override` (operator keep/drop) in `backend/src/admin_console/tests/test_refilter_api.py`

### Implementation for User Story 3

- [ ] T058 [US3] Implement `refilter.py`'s LLM half (`refilter_page`) and wire the LLM client from T030
- [ ] T059 [US3] Implement `refilter_link(link)` in `backend/src/admin_console/services.py`: fetch the page, derive the summary, call the LLM, persist verdict/plan type/confidence/flag, and advance or drop (FR-012..FR-015)
- [ ] T060 [US3] Implement `RefilterView`/`RefilterOverrideView` in `backend/src/admin_console/api.py` and wire routes
- [ ] T061 [P] [US3] Emit masked refilter events and build the link/refilter review page (`frontend/app/ops/sites/[siteId]/links/page.tsx`) with the override action
- [ ] T062 [P] [US3] Add Persian/RTL copy and frontend tests for the review page

**Checkpoint**: US1–US3 work independently.

---

## Phase 6: User Story 4 - Server-side headless capture (Priority: P4)

**Goal**: Capture each kept link headlessly on the server with domtrack and store the native trace.

**Independent Test**: Capture a kept link, confirm a `Trace` row with a UUID key and `is_valid_trace`, no operator fields, and no advance without a trace; emulate a capture failure and confirm no advance.

### Tests for User Story 4 ⚠️

- [ ] T063 [P] [US4] Contract test for `POST /api/v1/ops/links/{id}/captures` in `backend/src/admin_console/tests/test_capture_flow.py`: 201 recording a headless fixed-duration capture, 409 for a non-kept link, 409 `trace_required` when extraction is attempted without a trace (FR-016..FR-019, SC-009)
- [ ] T064 [P] [US4] Capture state-machine + artifact test in `backend/src/admin_console/tests/test_capture_state.py` and `test_artifact_storage.py`: only `stored`/`failed` leaves `recording`; one non-terminal session per link; `save_trace` writes through `STORAGES` under a UUID key and no `Trace` column holds the body (FR-053)

### Implementation for User Story 4

- [ ] T065 [US4] Implement `capture_headless` in `domtrack_client.py` (settle + scroll-to-bottom + fixed duration)
- [ ] T066 [US4] Implement `capture_link(link)` in `backend/src/admin_console/services.py`: create the session, run the headless capture, store the trace via `artifacts.save_trace`, advance the link, and map errors to `failed` (FR-016..FR-019)
- [ ] T067 [US4] Implement `CaptureStartView` in `backend/src/admin_console/api.py` and wire the route; add `run_capture_task` to `tasks.py`
- [ ] T068 [P] [US4] Emit masked capture events and build the pipeline stage badge (`frontend/src/features/ops/pipeline/StageBadge.tsx`); no capture UI action is required beyond status
- [ ] T069 [P] [US4] Add frontend tests for the stage badge and capture status in `frontend/tests/ops-capture.test.tsx`

**Checkpoint**: US1–US4 work independently.

---

## Phase 7: User Story 5 - Table extraction (domtrack tables extract) (Priority: P5)

**Goal**: Extract tables from each stored trace with domtrack, per page independent; deterministic.

**Independent Test**: Extract from a stored trace, persist tables/columns/rows; re-run and confirm identical rows; a trace with no tabular structure records zero tables.

### Tests for User Story 5 ⚠️

- [ ] T070 [P] [US5] Contract test for `POST /api/v1/ops/links/{id}/extractions` and `GET .../tables` in `backend/src/admin_console/tests/test_extraction.py`: tables persisted with domtrack's `path`/`atype`/`coverage`, `pipeline_stage="extracted"`, 409 without a trace, `table_count=0` records no tables (FR-020..FR-022)
- [ ] T071 [P] [US5] Determinism test in `backend/src/admin_console/tests/test_extraction_determinism.py`: extracting the same trace twice replaces the previous extraction and yields identical rows (FR-021, SC-010)

### Implementation for User Story 5

- [ ] T072 [US5] Implement `extract_tables` in `domtrack_client.py` and `extract_link_tables(link)` in `services.py` (transactional replace; per-page independent)
- [ ] T073 [US5] Implement `ExtractionView`/`LinkTablesView` in `backend/src/admin_console/api.py` and wire routes; add `run_extraction_task`
- [ ] T074 [P] [US5] Emit masked extraction events and build the tables page (`frontend/app/ops/links/[linkId]/tables/page.tsx`)

**Checkpoint**: US1–US5 work independently.

---

## Phase 8: User Story 6 - Table classification (Priority: P6)

**Goal**: Classify each extracted table as a plans table or not, with plan type and confidence.

**Independent Test**: A plans table and a non-plans table receive correct verdicts with confidence; a page with three tables where one is a plans table yields exactly one true verdict.

### Tests for User Story 6 ⚠️

- [ ] T075 [P] [US6] Classification test in `backend/src/admin_console/tests/test_classification.py`: one verdict per table with plan type + confidence, a page may hold several true verdicts, budget exhaustion parks the link (FR-023..FR-025, SC-011)
- [ ] T076 [P] [US6] Contract test for `POST /api/v1/ops/links/{id}/classifications` in `backend/src/admin_console/tests/test_classification_api.py`

### Implementation for User Story 6

- [ ] T077 [US6] Implement `classify_tables` in `llm.py` (Pydantic output) and `classify_link_tables(link)` in `services.py` (budget-gated)
- [ ] T078 [US6] Implement `ClassificationView` in `backend/src/admin_console/api.py` and wire the route; add `run_classification_task`
- [ ] T079 [P] [US6] Emit masked classification events and surface verdicts on the tables page

**Checkpoint**: US1–US6 work independently.

---

## Phase 9: User Story 7 - Plan schema extraction (data, not formulas) (Priority: P7)

**Goal**: Extract a list of plan records as data against the fixed schema; no selectors, no
formulas; skip unmappable tables.

**Independent Test**: A plans table yields normalized plan records; the output contains no selector/formula; an unmappable table is skipped while a sibling table is extracted.

### Tests for User Story 7 ⚠️

- [ ] T080 [P] [US7] Extraction test in `backend/src/admin_console/tests/test_plan_extraction.py`: normalized schema-shaped records, no selector/formula anywhere, per-table skip without dropping the page's mappable tables, idempotent re-extraction (FR-026..FR-031, SC-012, SC-013)
- [ ] T081 [P] [US7] Contract test for `POST /api/v1/ops/links/{id}/plans` and `GET .../plans` in `backend/src/admin_console/tests/test_plan_api.py`

### Implementation for User Story 7

- [ ] T082 [US7] Implement `extract_plans` in `llm.py` (validated against `plan_schema.py`; required-field check; normalized values)
- [ ] T083 [US7] Implement `extract_link_plans(link)` in `services.py`: extract per plans table, skip unmappable tables, upsert `PlanRecord` by `natural_key`, budget-gated (FR-026..FR-031)
- [ ] T084 [US7] Implement `PlansView` in `backend/src/admin_console/api.py` and wire the route to the combined `run_classification_task`; do not add a separate plan-extraction task
- [ ] T085 [P] [US7] Emit masked plan-extraction events and build the plans page (`frontend/app/ops/links/[linkId]/plans/page.tsx`)

**Checkpoint**: US1–US7 work independently.

---

## Phase 10: User Story 8 - Optional LLM labeling (Priority: P8)

**Goal**: Keep domtrack's labeling optional and admin-gated; it never gates another stage.

**Independent Test**: With labeling off the pipeline is unchanged; enabling it labels tables/columns; the pipeline still works when it is off.

### Tests for User Story 8 ⚠️

- [ ] T086 [P] [US8] Labeling gate test in `backend/src/admin_console/tests/test_labeling_gate.py`: off by default, enabled only by an admin, budget-gated, and the pipeline behaves identically with or without labels (FR-032..FR-035, SC-019)

### Implementation for User Story 8

- [ ] T087 [US8] Implement `label_tables` wiring in `domtrack_client.py` and a budget-gated `label_link_tables(link)` in `services.py`
- [ ] T088 [US8] Implement the labeling toggle endpoint and add `run_labeling_task`; register the toggle in `admin.py`
- [ ] T089 [P] [US8] Surface labels on the tables page and add Persian/RTL copy

**Checkpoint**: US1–US8 work independently.

---

## Phase 11: User Story 9 - Publishing to the main site (Priority: P9)

**Goal**: Publish extracted plan records through `catalog` with provenance; retire removed items.

**Independent Test**: Extract → publish and confirm `catalog.PublishedRecord` rows with site/link/trace/classification provenance; a replay removal retires the record; `catalog` never imports `admin_console`.

### Tests for User Story 9 ⚠️

- [ ] T090 [P] [US9] Publishing test in `backend/src/admin_console/tests/test_publishing.py`: publish through `CatalogInterface` with site/link/trace/classification provenance and upsert by `(source, site, natural_key)`; removal retires; a plan with an unpopulated required field is not published (FR-030, FR-036..FR-038, SC-013)
- [ ] T091 [P] [US9] Contract test for `POST /api/v1/ops/links/{id}/publish` in `backend/src/admin_console/tests/test_publish_api.py`

### Implementation for User Story 9

- [ ] T092 [US9] Implement `publish_link_plans(link)` in `services.py` calling `CatalogInterface.upsert_published_record`/`retire_published_record`; implement `CatalogInterface` in `catalog/interfaces.py`
- [ ] T093 [US9] Implement `PublishView` in `backend/src/admin_console/api.py` and wire the route
- [ ] T094 [P] [US9] Emit masked publish/retire events and build the publish/provenance page

**Checkpoint**: US1–US9 work independently.

---

## Phase 12: User Story 10 - Scheduled replay, change detection, conditional re-extraction (Priority: P10)

**Goal**: Replay with domtrack compare, classify changes content/structural, re-extract only when
a plans table is touched, and alert on failure-rate crossings.

**Independent Test**: Replay due links; a change to a plans table re-extracts while a change elsewhere does not; a structural change re-discovers/re-classifies first; crossing the failure threshold raises one in-app notification naming the link.

### Tests for User Story 10 ⚠️

- [ ] T095 [P] [US10] Replay test in `backend/src/admin_console/tests/test_replay_diff.py`: due links replayed with `compare`, before/after traces recorded, changes classified content/structural, `reextracted=true` only when a plans table is touched, and removals retire published records (FR-039..FR-043, SC-014, SC-015)
- [ ] T096 [P] [US10] Scheduler test in `backend/src/admin_console/tests/test_replay_scheduler.py`: `run_scheduled_replays` selects due active-site links, skips suspended sites, enqueues one `django.tasks` task per link, no Celery
- [ ] T097 [P] [US10] Failure-rate/alert test in `backend/src/admin_console/tests/test_failure_alerts.py`: rate derives from domtrack failures over the window, exactly one `open` alert per crossing, resolved on a fall, re-opened on a later rise (FR-044, SC-017)

### Implementation for User Story 10

- [ ] T098 [US10] Implement `compare_replay` wiring in `domtrack_client.py` and `execute_replay_run(link)` in `replay.py`: materialize the before trace, run compare, store the after trace, classify changes (content/structural), map each change to a classification (structural ⇒ re-discover + re-classify first), re-extract only when a plans table is touched, apply updates via `CatalogInterface`, and recompute the failure rate (FR-039..FR-043)
- [ ] T099 [US10] Implement `evaluate_failure_alert(link)` in `services.py` (state-based; one notification per crossing via `notifications.interfaces.notify`) and `rerun_link_stages(link, actor)` resetting to `discovered` (FR-044..FR-046)
- [ ] T100 [US10] Complete `run_scheduled_replays` and `run_replay_task`
- [ ] T101 [US10] Implement `ReplayRunListView`/`ReplayRunCreateView`, `LinkFailureView`, `AlertListView`, `LinkRerunView`, and the recipient endpoints in `api.py`; wire routes
- [ ] T102 [US10] Wire the `notifications` app API for the in-app inbox and recipient management
- [ ] T103 [P] [US10] Emit masked replay/alert/delivery events and build the replay & alerts page (`frontend/app/ops/replay/page.tsx`) with a re-run action
- [ ] T104 [P] [US10] Add Persian/RTL copy and frontend tests in `frontend/tests/ops-replay.test.tsx`

**Checkpoint**: All ten stories work independently; the data self-refreshes with alerting.

---

## Phase 13: Polish & Cross-Cutting Concerns

**Purpose**: Resilience, budget controls, contract, masking, and boundary guarantees

- [ ] T105 [P] Implement per-link isolation + retry/backoff + dead-lettering around every stage in `tasks.py`/`services.py` and add `backend/src/admin_console/tests/test_resilience.py` (FR-051, FR-052, SC-017)
- [ ] T106 [P] Implement the token-budget controls (admin set/get) and the awaiting-budget queue/resume path; add `backend/src/admin_console/tests/test_budget_gating.py` (FR-047..FR-050, SC-016)
- [ ] T107 [P] Add the settings page (`frontend/app/ops/settings/page.tsx`) for the token budget, crawl query/bounds, deny list, refilter threshold, capture duration, and replay period
- [ ] T108 [P] Contract test for the whole API against `contracts/ops-console-api.md`
- [ ] T109 [P] Masked-log audit across all events (SC-021)
- [ ] T110 [P] Domtrack/crawl4ai import-boundary test: `domtrack` only in `domtrack_client.py`, `crawl4ai` only in `discovery.py` (SC-020)
- [ ] T111 Run the quickstart.md validation scenarios and record the results (browser/network stages are manual and recorded as such)
- [X] T112 [US10] Fix the link retry button so a successful rerun request immediately displays and disables as queued; reconcile the optimistic state when fresh link data arrives.
- [X] T113 [US3] Refilter all eligible links in one LLM request using numeric indexes, including each link's URL, h1–h3 headings, and important text; persist each Boolean verdict and stop rejected links before capture.
- [X] T114 [US6][US7] Combine table classification and plan extraction in one LLM request: rejected tables return only an incorrect-class Boolean; accepted tables also return schema-validated extracted plan data.
- [X] T115 [US3][US6][US7] Update regression coverage and API/task documentation for retry feedback, batched refilter, and combined table classification/extraction.

**Checkpoint**: The feature is complete, contract-verified, and validated end-to-end.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS all user stories**
- **User Stories (Phases 3–12)**: All depend on Foundational; stories can then proceed in parallel (if staffed) or sequentially P1 → P10
- **Polish (Phase 13)**: Depends on all desired stories being complete

### User Story Dependencies

- **US1 (P1)**: No dependencies — creates the `Site` later stories use; MVP
- **US2 (P2)**: Depends on US1 for an approved company's `Site`; independently testable by seeding an approved company and a stubbed crawler
- **US3 (P3)**: Depends on US2's candidate links; independently testable with a seeded candidate and a stubbed LLM
- **US4 (P4)**: Depends on US3 keeping a link; independently testable with a seeded kept link and a stubbed capture
- **US5 (P5)**: Depends on a stored trace (US4); independently testable with a seeded trace
- **US6 (P6)**: Depends on extracted tables (US5); independently testable with seeded tables
- **US7 (P7)**: Depends on plans-table classifications (US6)
- **US8 (P8)**: Depends on extracted tables (US5); independent of US6/US7 (labels optional)
- **US9 (P9)**: Depends on plan records (US7); publishes through `catalog` (foundational interface)
- **US10 (P10)**: Depends on plan records + published data (US7, US9); raises alerts through `notifications` (foundational interface)

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models were completed in Foundational; per story: serializers → selectors/services → endpoints → frontend
- Core implementation before frontend integration
- Story complete and independently validated before moving to the next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational model tasks marked [P] run in parallel (T012–T024), then T025 migrates
- Once Foundational completes, US1–US10 can be staffed in parallel (subject to the dependencies above)
- Within a story, all test tasks marked [P] run in parallel, and all frontend copy/tests tasks marked [P] run in parallel

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (approval queue + decisions)
4. **STOP and VALIDATE**: run `test_approval_queue.py` and `test_approval_authorization.py`, then exercise V1 from quickstart.md
5. Deploy/demo if ready — operators can clear the verification queue

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → validate (MVP: company approval)
3. US2 → validate (candidate links flowing)
4. US3 → validate (refilter drops non-plans pages before Chrome)
5. US4 → validate (headless traces entering the platform)
6. US5 → validate (tables persisted, deterministic)
7. US6 → validate (plans tables identified with confidence)
8. US7 → validate (plan data extracted, no recipes)
9. US8 → validate (optional labels)
10. US9 → validate (published with provenance)
11. US10 → validate (self-refreshing data with alerting)
12. Polish → resilience, budget, contract, masking, boundary guarantees

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps each task to its user story for traceability
- Every task names an exact file path so it is executable without extra context
- No Celery anywhere: background work is `django.tasks` (T007) plus `run_scheduled_replays` (T100)
- domtrack is imported only in `backend/src/admin_console/domtrack_client.py` (T028, locked by T110); crawl4ai only in `discovery.py` (T029)
- The operator console is `/api/v1/ops/` and `frontend/app/ops/**` — never `/admin`
- Published records live in `catalog` (T024/T033), notifications in `notifications` (T034)
- **No recipes, no formulas, no Handsontable, no sitemap** anywhere in this task list
