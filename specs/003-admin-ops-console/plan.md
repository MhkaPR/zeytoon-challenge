# Implementation Plan: Admin Console — Company Approval & Site Data Maintenance

**Branch**: `003-admin-ops-console` | **Date**: 2026-10-27 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-admin-ops-console/spec.md`

## Summary

Deliver the operator console for the host/server plan aggregator: a) **company approval** and
b) **site data maintenance** driven end-to-end by the mandated `domtrack` library. The console
lists companies awaiting verification with the information needed to decide (including a
duplicate-domain warning), records exactly one append-only decision per company (approved ⇒
verified, panel opens, its site's maintenance lifecycle starts; not approved ⇒ stays
unverified, registration step reopens), and refuses any owner attempt to influence the
outcome. On approval, the company's single site is onboarded: candidate links are
auto-discovered from its sitemap (or entered by the operator), reviewed (kept or removed), and
the kept links enter the pipeline. Each kept link is captured by **domtrack capture** running
locally on the operator's machine (a Chrome window opens, recording starts and ends
interactively), and the resulting native trace file is transferred to the platform
automatically where the browser permits and by operator-confirmed manual upload otherwise.
The stored trace is mined for tables with **domtrack tables extract**, optionally enriched by
**domtrack tables label** (admin-gated, LLM cost-ceiling aware), mapped to a code-defined
**plan schema** in a Handsontable workspace that records, per schema field, the source
selector (the column's domtrack `path`) and a combination formula — the extraction recipe,
whose formula is an Excel/spreadsheet-compatible expression so operators work with familiar
spreadsheet semantics — then cleaned into filterable values and published to the main site
with full provenance. A scheduled **domtrack replay + record + compare/diff** run refreshes
published data, applies added/removed/changed differences, tracks a per-link failure rate,
and raises notifications to an admin-configurable recipient list when a link's failure rate
crosses the configured threshold, so the operator can re-run that link's stages. Background
work uses **Django 6's built-in Tasks framework** plus a `run_scheduled_replays` management
command — **Celery is not used**. Every tunable is a django-constance runtime constant, no
domtrack capability is reimplemented, and the pipeline runs in a new `admin_console` backend
module that consumes company state only through `companies/interfaces.py`, writes published
data into the `catalog` app through its interface, and dispatches all notifications through a
dedicated `notifications` app.

## Technical Context

**Language/Version**: Python 3.14 (backend), TypeScript 5 / Node 20+ (frontend)

**Primary Dependencies**: Django 6.1.2, Django REST Framework 3.18, **Django Tasks
(`django.tasks`, the framework's built-in background-work system — Celery is explicitly not
used)**, django-guardian (role + object permissions), django-constance with the database
backend (runtime constants), Pydantic (boundary validation + recipe validation),
drf-spectacular (OpenAPI), **domtrack 2.0.0** (capture, replay, record-during-replay, compare,
diff, HTML rebuild, table discovery, LLM table labeling — consumed as-is), **django-storages
+ boto3** for S3-backed artifacts via Django's `STORAGES` setting, and `httpx` + stdlib
`xml.etree` (sitemap fetching/parsing). Reuses the existing `accounts` JWT auth, `utils`
shared base/logging, and `companies` module through its interface. Frontend: Next.js 16.4.2,
React 19.3, Tailwind 4, HeroUI v3, Vitest + Testing Library, and **Handsontable**
(`handsontable` + `@handsontable/react-wrapper`) for the mapping spreadsheet.

**Storage**: PostgreSQL is the source of truth for Site, Link, CaptureSession, Trace metadata,
ExtractedTable/Column/Row, SemanticLabel, ExtractionRecipe/RecipeFieldBinding, ReplayRun, and
LlmCostLedger (the plan schema is code, not a table). **Published records live in the
`catalog` app** and notifications live in the **`notifications` app** (see Project
Structure). domtrack **trace files and other artifacts are stored through Django's `STORAGES`
API**, defaulting to S3-compatible object storage (`django-storages`/`boto3`) and
configurable per environment to local filesystem or another backend; the database stores only
the storage-backed key, backend alias, byte size, and content hash, never the trace body.
Redis backs the cache and throttles. Meilisearch is not involved (search/ranking are owned
elsewhere).

**Testing**: pytest + pytest-django with DRF `APITestCase`/`APIClient` covering approval
recording and owner refusal, sitemap discovery + manual entry + link review state, capture
session state machine (no advance without a stored trace), extraction determinism and
empty-table flagging, labeling gating + ceiling stop, recipe completeness, formula validity at
the boundary, and restore-on-reopen, cleaning outcomes/exceptions, publishing through the
`catalog` interface with provenance and removal handling, notification fan-out through the
`notifications` app (in-app only; email is out of scope by project decision), replay/compare/diff application, failure-rate threshold
and one-shot alerting, artifact storage through a `STORAGES`-backed backend, constance-driven
tuning, and log masking (SC-018). A dedicated import test asserts every `domtrack` import lives
in `admin_console/domtrack_client.py` (SC-017). Frontend: Vitest + Testing Library for the
approval queue, link review, capture controls, mapping workspace restore/save, and alerts.

**Target Platform**: Linux server (Docker), all services hosted in Iran, including a
self-hosted S3-compatible object store for artifacts; the operator console is a role-gated
area of the existing Next.js app. domtrack capture runs as a local FastAPI service on the
operator's own machine.

**Project Type**: Web application (backend API + frontend), modular monolith.

**Performance Goals**: Sustain 100 req/s at peak for console read endpoints (read-heavy
profile); console list/queue endpoints p95 < 300 ms; the scheduled replay command's enqueue
step is independent of per-link work (each link runs as its own task); published data
staleness bounded by the configured replay period; trace reads/writes served by the object
store rather than the database.

**Constraints**: domtrack MUST be used as-is for every capability it provides and none may be
reimplemented (FR-000/000a/000b, SC-017); the stored artifact MUST be domtrack's native trace
(FR-000a); trace bodies MUST NOT be converted into platform tables and MUST NOT be stored in
the database; capture MUST NOT advance a link without a stored trace (FR-014); a link MUST NOT
be mapped or published with a required schema field unconnected (FR-030); recipe formulas MUST
be Excel/spreadsheet-valid expressions over source selectors; labeling MUST be off by default
and MUST stop at the LLM ceiling rather than overspend (FR-021, FR-024); no unmasked personal
data in any log (SC-018); no Celery; no hard-coded tunables; crawling must respect robots.txt
with a transparent user-agent and per-domain rate limiting (Principle X); data and services
hosted in Iran.

**Scale/Scope**: Hundreds of approved companies/sites, each with a maintained link set; a
console area of ~8 screens (approval queue, site detail, link review, capture, tables, mapping
workspace, cleaning/publish, replay & alerts, settings); 8 pipeline stories (P1–P8), ~46
functional requirements, 18 success criteria; a new `admin_console` Django app (~20 endpoints)
plus a new `notifications` app and the `catalog` app's published-record model, and role-gated
operator frontend routes under `/ops`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|-----------|------|--------|
| I. Product Domain | Company approval and site data maintenance are the provider data-ingestion path for the plan comparison product; the published records this feature produces are the (plan) data the catalog and search features consume. | PASS |
| II. Cost and External Resources | LLM cost ceiling stored in a Django model (not settings), checked before each domtrack labeling call; exceeding it stops labeling and alerts rather than overspending (FR-024). | PASS |
| III. Security and Secrets | LLM provider and S3 credentials read only from environment; trace metadata validated with Pydantic at the upload boundary; no key in code (including no inline S3 credentials — the storage backend reads them from env). | PASS |
| IV. Data Governance | Postgres/Redis and the S3-compatible artifact store all run in Iran; `django-storages` is pointed at the self-hosted endpoint, so no external/cloud dependency; Meilisearch untouched here. | PASS |
| V. Architecture | New `admin_console`, `notifications`, and `catalog` changes are all inside the modular monolith; company state reached only via `companies/interfaces.py`, published records written only via `catalog/interfaces.py`, and notifications dispatched only via `notifications/interfaces.py`; Postgres is the source of truth; Redis used for caching/throttles; single deployable with the operator area inside the existing Next.js app. | PASS |
| VI. Performance and Scalability | Read-heavy console endpoints targeted at 100 req/s with p95 < 300 ms for queue/list reads; replay job enqueue decoupled from per-link work via Django Tasks; traces served from object storage so large artifacts never hit Postgres; Redis caching for repeated reads. | PASS |
| VII. Observability | Structured JSON events at debug/info/warning/error for every pipeline transition, with the required metrics (crawl success rate per provider, latency per source, LLM call count + cost, replay staleness) and aggregation/sampling on hot paths. | PASS |
| VIII. Quality and Testing | Every domain behavior (each stage and each gate) ships with an automated test; a domtrack-import test locks SC-017, and a formula-validation test locks Excel/spreadsheet compatibility so neither can regress. | PASS |
| IX. Data Retention | Traces, recipes, replay runs, and alerts are retained for auditing (artifacts in object storage, metadata in Postgres); links are never hard-deleted (removal is a recorded state); traces remain the evidence for published data. | PASS |
| X. Crawling Ethics | Sitemap/link fetching honors robots.txt, uses a transparent user-agent with contact URL, and applies per-domain rate limiting. | PASS |
| XI. Authentication | Operator console reuses the existing JWT auth; every endpoint is operator gated (`ops` group or admin, `is_operator()`) and refuses owner access to decisions (FR-005). | PASS |
| XII. Prefer Established Libraries and Generators | `startapp` scaffolds `admin_console` and `notifications`; domtrack is used as-is (no reimplementation); `django-storages`/`boto3` provide S3 artifacts instead of hand-written storage code; constance, guardian, DRF, and Handsontable are established libraries; sitemap parsing uses stdlib where no library clearly adds value (research R5). | PASS |
| XIII. Configurable Values | All tunables are django-constance constants except the LLM ceiling (model-backed per Principle II) and environment-specific values (settings/env), which now explicitly include the artifact storage backend and S3 endpoint/credentials; no hard-coded thresholds or inline storage config. | PASS |

**Post-Phase 1 re-check**: PASS. Revised Phase 1 design keeps the module boundaries strict:
`admin_console` writes published records only through `catalog/interfaces.py` and emits
notifications only through `notifications/interfaces.py`, so `catalog` and `notifications`
remain independently owned and reusable (Principle V). The artifact layer is delegated to
Django's `STORAGES` API with an S3 default configurable from settings (Principle XII, XIII),
and recipe formulas are constrained to an Excel-compatible grammar (a boundary validation
rule, not new complexity). Complexity Tracking remains empty.

## Project Structure

### Documentation (this feature)

```text
specs/003-admin-ops-console/
├── plan.md              # This file ($speckit-plan command output)
├── research.md          # Phase 0 output ($speckit-plan command)
├── data-model.md        # Phase 1 output ($speckit-plan command)
├── quickstart.md        # Phase 1 output ($speckit-plan command)
├── contracts/           # Phase 1 output ($speckit-plan command)
└── tasks.md             # Phase 2 output ($speckit-tasks command - NOT created by $speckit-plan)
```

### Source Code (repository root)

```text
backend/
└── src/
    ├── config/
    │   ├── settings.py            # register admin_console + notifications; TASKS setting;
    │   │                          #   CONSTANCE_CONFIG additions; STORAGES (S3 default via
    │   │                          #   django-storages, env-configurable); DOMTRACK_LOCAL_API_URL;
    │   │                          #   email backend
    │   └── urls.py                # mount /api/v1/ops/ (operator console API)
    ├── utils/                     # unchanged (TimestampedModel, logging/masking reused)
    ├── accounts/                  # operator identity; ops/admin groups + is_operator()
    ├── companies/                 # unchanged; consumed only through interfaces.py
    │   └── interfaces.py          # CompaniesInterface.record_verification_decision (approval)
    ├── catalog/                   # EXISTING app; gains the published-record model
    │   ├── models.py              # + PublishedRecord (plan data consumed by search/catalog)
    │   ├── interfaces.py          # NEW: upsert/retire published records for other modules
    │   ├── services.py            # NEW: publish/retire logic (provenance preserved)
    │   └── migrations/
    ├── notifications/             # NEW general-purpose app (python manage.py startapp)
    │   ├── models.py              # Notification, NotificationRecipient,
    │   │                          #   NotificationDelivery (in-app channel)
    │   ├── interfaces.py          # NEW: notify(recipients, event, ...) entry point
    │   ├── services.py            # dispatch, recipient add/remove, delivery bookkeeping
    │   ├── channels.py            # in-app channel implementation
    │   ├── api.py                 # admin endpoints: recipients, notification inbox
    │   ├── tasks.py               # django.tasks delivery jobs
    │   ├── migrations/
    │   └── tests/
    ├── admin_console/             # NEW module (python manage.py startapp admin_console)
    │   ├── models.py              # Site, Link, CaptureSession, Trace, ExtractedTable,
    │   │                          #   ExtractedTableColumn, ExtractedTableRow, SemanticLabel,
    │   │                          #   ExtractionRecipe, RecipeFieldBinding, ReplayRun,
    │   │                          #   LlmCostLedger
    │   ├── interfaces.py          # the only sanctioned entry point for other modules
    │   ├── domtrack_client.py     # ONLY module that imports domtrack (FR-000, SC-017):
    │   │                          #   local REST capture + server-side library adapters
    │   ├── artifacts.py           # Django STORAGES-backed artifact store (S3 default);
    │   │                          #   uuid-keyed writes/reads/deletes, never touches Postgres
    │   ├── plan_schema.py         # code-defined plan schema with plan-type dimension (FR-027)
    │   ├── formulas.py            # Excel/spreadsheet-compatible formula grammar + evaluator
    │   ├── discovery.py           # robots.txt + sitemap discovery (stdlib xml + httpx)
    │   ├── cleaning.py            # cleaning rules engine (constance-driven, FR-032..034)
    │   ├── services.py            # approvals (via interface), onboarding, review, capture
    │   │                          #   session, extraction, labeling gate, recipe save/validate,
    │   │                          #   cleaning, publish (via catalog interface),
    │   │                          #   replay orchestration, alerting (via notifications interface)
    │   ├── tasks.py               # django.tasks task functions (extract, label, replay link)
    │   ├── selectors.py           # console reads (queue, site detail, tables, recipes, runs)
    │   ├── serializers.py         # DRF I/O + Pydantic boundary/recipe schemas
    │   ├── api.py                 # DRF views (OperatorOnlyView base) for console endpoints
    │   ├── constants.py           # constance CONSTANCE_CONFIG additions (runtime tunables)
    │   ├── events.py              # structured, masked pipeline events (Principle VII, FR-044)
    │   ├── admin.py               # operator surfaces: toggle labeling, costs (Django admin)
    │   ├── management/
    │   │   └── commands/
    │   │       └── run_scheduled_replays.py   # due-run scanner; enqueues per-link tasks
    │   ├── migrations/
    │   └── tests/
    │       ├── test_approval_queue.py
    │       ├── test_site_onboarding.py
    │       ├── test_link_review.py
    │       ├── test_capture_flow.py
    │       ├── test_extraction.py
    │       ├── test_labeling_gate.py
    │       ├── test_mapping_recipe.py
    │       ├── test_formula_excel_compat.py
    │       ├── test_artifact_storage.py     # STORAGES-backed, uuid keys, no DB blobs
    │       ├── test_cleaning.py
    │       ├── test_publishing.py           # written via catalog interface + provenance
    │       ├── test_replay_diff.py
    │       ├── test_failure_alerts.py       # alerting via notifications interface
    │       ├── test_domtrack_reuse.py       # asserts domtrack imported only in client
    │       └── test_log_masking.py
    └── manage.py

frontend/
├── app/
│   └── ops/                       # NEW role-gated operator console (NOT /admin)
│       ├── layout.tsx             # operator guard + console shell
│       ├── page.tsx               # approvals queue
│       ├── companies/[companyId]/page.tsx
│       ├── sites/[siteId]/page.tsx            # site detail + pipeline stage
│       ├── sites/[siteId]/links/page.tsx      # link review
│       ├── links/[linkId]/capture/page.tsx    # capture trigger + trace upload
│       ├── links/[linkId]/tables/page.tsx     # extracted tables + labels
│       ├── links/[linkId]/mapping/page.tsx    # Handsontable mapping workspace
│       ├── links/[linkId]/publish/page.tsx    # cleaning exceptions + publish
│       ├── replay/page.tsx                    # replay runs + failure alerts
│       └── settings/page.tsx                  # labeling toggle, recipients, tunables
└── src/
    ├── features/
    │   └── ops/                   # NEW feature slices (approvals, links, capture,
    │       │                      #   tables, mapping, publishing, replay, settings)
    │       └── mapping/MappingWorkspace.tsx     # Handsontable-based workspace
    └── lib/
        ├── api/ops.ts             # console API client (follows api/companies.ts pattern)
        └── i18n/                  # Persian/RTL copy additions

specs/003-admin-ops-console/       # this feature's design artifacts
```

**Structure Decision**: Three module boundaries, each justified by ownership rather than
convenience:

- **`admin_console` (new)** owns the site-maintenance pipeline (Site, Link, CaptureSession,
  Trace metadata, extracted tables, labels, recipes, replay runs, cost ledger), the
  artifact-store adapter, and the approval *queue* surface. Company verification itself is
  delegated to `companies.services.record_verification_decision` through
  `companies/interfaces.py`, so `VerificationDecision` keeps its single owner and SC-001
  stays structurally true. All domtrack usage is funnelled through
  `admin_console/domtrack_client.py` so FR-000/SC-017 are auditable, and background work runs
  through `admin_console/tasks.py` (Django Tasks) triggered by the `run_scheduled_replays`
  management command — no Celery, no separate worker framework.
- **`catalog` (existing, extended)** owns published plan records, because they are the plan
  data consumed by catalog and search; `admin_console` publishes only through
  `catalog/interfaces.py`, never by touching `catalog` tables.
- **`notifications` (new, general-purpose)** owns notification events, recipients, and
  channel (in-app; email is out of scope by project decision), because notifications are a platform capability used beyond this
  feature; `admin_console` raises alerts only through `notifications/interfaces.py`.

Artifacts (domtrack traces and related files) are written through `admin_console/artifacts.py`
on top of Django's `STORAGES` API: the default alias is S3-compatible object storage via
`django-storages` + `boto3`, and a developer/devops can switch the backend (for example to
local filesystem) purely from settings without code changes. Object keys are UUID-based, so
every stored artifact has a unique, non-guessable name independent of its original path; the
database stores only the key, backend alias, size, and hash. The operator UI is a role-gated
frontend area at `frontend/app/ops/**` with slices under `frontend/src/features/ops/**` and an
`api/ops.ts` client — deliberately **not** `app/admin/**`, so the frontend route never shadows
or reads like Django's built-in `/admin/`, and the console API is mounted at `/api/v1/ops/`.
The mapping workspace uses Handsontable as the spec requires, and its formulas are validated
against an Excel/spreadsheet-compatible grammar so operators can reason about them as
spreadsheet expressions.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations. Table intentionally empty.
