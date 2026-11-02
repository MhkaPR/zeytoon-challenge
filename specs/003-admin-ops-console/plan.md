# Implementation Plan: Admin Console — Company Approval & Site Data Maintenance

**Branch**: `003-admin-ops-console` | **Date**: 2026-10-27 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-admin-ops-console/spec.md`

## Summary

Deliver the operator console for the host/server plan aggregator: a) **company approval** and the
operator controls for b) an **automated site-data pipeline** driven by the mandated `domtrack`
library plus `crawl4ai`. The console lists companies awaiting verification with the information
needed to decide (including a duplicate-domain warning), records exactly one append-only decision
per company (approved ⇒ verified, panel opens, its site's maintenance lifecycle starts; not
approved ⇒ stays unverified, registration step reopens), and refuses any owner attempt to
influence the outcome. On approval, the company's single site is onboarded by **crawl4ai adaptive
crawling** (statistical strategy — no embeddings, no LLM) seeded on the company domain; this
replaces sitemap discovery. Harvested links are reduced by a deterministic host/extension/segment
policy, then **refiltered by an LLM** that receives only the link URL, its `h1–h3`, and the
important section (largest text-density block in `<main>`/`<article>`) derived without an LLM;
only confidently non-plans links are dropped. Each kept link is captured **headlessly by domtrack
on the server** (fixed-duration recording with a settle/scroll step) and stored as a native
trace. The trace is mined for tables with **domtrack tables extract** (each page independent),
each table is **classified by an LLM** as a plans table or not with a confidence, and every plans
table is **extracted as data by an LLM against the code-defined plan schema** — normalized plan
records, no selectors and no formulas — optionally enriched by **domtrack tables label**
(admin-gated). Extracted plan records are published to the main site through the `catalog` app
with provenance. A scheduled **domtrack compare** run (replay + record + diff in one call)
classifies each detected change as content or structural; a change touching a plans table
triggers LLM re-extraction (structural changes re-discover and re-classify first), while a change
elsewhere triggers no LLM work. An admin-set **LLM token budget** gates
refilter/classification/extraction/labeling: when it is exhausted the rest of the pipeline
continues and only LLM-gated work waits. A per-link failure rate raises notifications to an
admin-configurable recipient list, and every stage is isolated and retried with backoff before
dead-lettering. Background work uses **Django 6's built-in Tasks framework** plus a
`run_scheduled_replays` management command — **Celery is not used**. Every tunable is a
django-constance runtime constant, no domtrack capability is reimplemented, and the pipeline runs
in `admin_console`, which consumes company state only through `companies/interfaces.py`, writes
published data into `catalog` through its interface, and dispatches all notifications through a
dedicated `notifications` app.

## Technical Context

**Language/Version**: Python 3.14 (backend), TypeScript 5 / Node 20+ (frontend)

**Primary Dependencies**: Django 6.1.2, Django REST Framework 3.18, **Django Tasks
(`django.tasks`, the framework's built-in background-work system — Celery is explicitly not
used)**, django-guardian (role + object permissions), django-constance with the database
backend (runtime constants), Pydantic (boundary validation + the plan-schema models the LLM
extraction fills), drf-spectacular (OpenAPI), **domtrack** (capture, replay,
record-during-replay, compare, diff, HTML rebuild, table discovery, LLM table labeling —
consumed as-is; server-side and headless), **crawl4ai** (adaptive crawling with the
statistical strategy for link discovery), an **OpenAI-compatible client** for the
refilter/classification/extraction LLM calls (base URL + key from environment; `openai` or
`compatible`), **django-storages + boto3** for S3-backed artifacts via Django's `STORAGES`
setting, and `httpx` (the page fetch behind the refilter's deterministic extraction). Reuses
the existing `accounts` JWT auth, `utils` shared base/logging, and `companies` module through
its interface. Frontend: Next.js 16.4.2, React 19.3, Tailwind 4, HeroUI v3, and Vitest +
Testing Library (no mapping spreadsheet).

**Storage**: PostgreSQL is the source of truth for Site, Link, CaptureSession, Trace metadata,
ExtractedTable/Column/Row, TableClassification, PlanRecord, SemanticLabel, ReplayRun,
LlmCostLedger, and the LLM token budget (the plan schema is code, not a table). **Published
records live in the
`catalog` app** and notifications live in the **`notifications` app** (see Project
Structure). domtrack **trace files and other artifacts are stored through Django's `STORAGES`
API**, defaulting to S3-compatible object storage (`django-storages`/`boto3`) and
configurable per environment to local filesystem or another backend; the database stores only
the storage-backed key, backend alias, byte size, and content hash, never the trace body.
Redis backs the cache and throttles. Meilisearch is not involved (search/ranking are owned
elsewhere).

**Testing**: pytest + pytest-django with DRF `APITestCase`/`APIClient` covering approval
recording and owner refusal, adaptive-crawl link discovery (stubbed crawler) plus the
deterministic host/extension/segment policy, the refilter input shape (URL + `h1–h3` +
important section, never HTML) and its recall-biased keep/drop rule, the headless capture state
machine (no advance without a stored trace), extraction determinism and no-tables recording,
table classification, schema extraction producing normalized plan data with no
recipe/selector/formula, per-table skip without dropping a page's mappable tables, budget
gating and the awaiting-budget queue, replay/content-vs-structural classification and
conditional re-extraction, resilience (per-link isolation, retry/backoff, dead-letter),
publishing through the `catalog` interface with provenance and removal handling, notification
fan-out through the `notifications` app (in-app only; email is out of scope by project
decision), failure-rate threshold and one-shot alerting, artifact storage through a
`STORAGES`-backed backend, constance-driven tuning, and log masking (SC-021). Dedicated import
tests assert every `domtrack` import lives in `admin_console/domtrack_client.py` and every
`crawl4ai` import lives in the discovery module (SC-020). Frontend: Vitest + Testing Library
for the approval queue, link/refilter review, and alerts.

**Target Platform**: Linux server (Docker), all services hosted in Iran, including a
self-hosted S3-compatible object store for artifacts; the operator console is a role-gated
area of the existing Next.js app. **domtrack and crawl4ai run server-side**, with a headless
Chromium available to the server; no operator machine runs domtrack.

**Project Type**: Web application (backend API + frontend), modular monolith.

**Performance Goals**: Sustain 100 req/s at peak for console read endpoints (read-heavy
profile); console list/queue endpoints p95 < 300 ms; the scheduled replay command's enqueue
step is independent of per-link work (each link runs as its own task); published data
staleness bounded by the configured replay period; trace reads/writes served by the object
store rather than the database.

**Constraints**: domtrack MUST be used as-is for every capability it provides and none may be
reimplemented (FR-000/000a/000b, SC-020); the stored artifact MUST be domtrack's native trace
(FR-000a); trace bodies MUST NOT be converted into platform tables and MUST NOT be stored in
the database; capture MUST be headless and server-side and MUST NOT advance a link without a
stored trace (FR-016, FR-018); link discovery MUST use crawl4ai's statistical strategy with no
embeddings/LLM and MUST NOT fetch a sitemap (FR-008); the refilter MUST send no page HTML to the
model (FR-012); extraction MUST produce data only, with no selectors, formulas, or recipes
(FR-028); labeling MUST be off by default and MUST respect the token budget rather than
overspend (FR-032, FR-035); when the token budget is exhausted only LLM-gated work waits and the
rest of the pipeline continues (FR-048); each link is isolated and retries with backoff before
dead-lettering (FR-051, FR-052); no unmasked personal data in any log (SC-021); no Celery; no
hard-coded tunables; crawling and capture must respect robots.txt with a transparent user-agent
and per-domain rate limiting (Principle X); data and services hosted in Iran.

**Scale/Scope**: Hundreds of approved companies/sites, each with a maintained link set; a
console area of ~7 screens (approval queue, site detail, link/refilter review, tables &
classifications, plan data, replay & alerts, settings); 10 pipeline stories (P1–P10), ~58
functional requirements, 21 success criteria; a new `admin_console` Django app (~20 endpoints)
plus a new `notifications` app and the `catalog` app's published-record model, and role-gated
operator frontend routes under `/ops`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|-----------|------|--------|
| I. Product Domain | Company approval and site data maintenance are the provider data-ingestion path for the plan comparison product; the published records this feature produces are the (plan) data the catalog and search features consume. | PASS |
| II. Cost and External Resources | The admin-set LLM token budget is stored in a Django model (not settings) and checked before every LLM-gated call (refilter, classification, schema extraction, labeling); when exhausted, non-LLM stages continue and LLM-gated work waits, with the admin notified (FR-047..FR-049). Per-link/per-table spend is attributed and retried calls are idempotent (FR-049, FR-050). | PASS |
| III. Security and Secrets | LLM provider and S3 credentials read only from environment; trace metadata validated with Pydantic at the upload boundary; no key in code (including no inline S3 credentials — the storage backend reads them from env). | PASS |
| IV. Data Governance | Postgres/Redis and the S3-compatible artifact store all run in Iran; `django-storages` is pointed at the self-hosted endpoint, so no external/cloud dependency; Meilisearch untouched here. | PASS |
| V. Architecture | New `admin_console`, `notifications`, and `catalog` changes are all inside the modular monolith; company state reached only via `companies/interfaces.py`, published records written only via `catalog/interfaces.py`, and notifications dispatched only via `notifications/interfaces.py`; Postgres is the source of truth; Redis used for caching/throttles; single deployable with the operator area inside the existing Next.js app. | PASS |
| VI. Performance and Scalability | Read-heavy console endpoints targeted at 100 req/s with p95 < 300 ms for queue/list reads; replay job enqueue decoupled from per-link work via Django Tasks; traces served from object storage so large artifacts never hit Postgres; Redis caching for repeated reads. | PASS |
| VII. Observability | Structured JSON events at debug/info/warning/error for every pipeline transition, with the required metrics (crawl success rate per provider, latency per source, LLM call count + cost, replay staleness) and aggregation/sampling on hot paths. | PASS |
| VIII. Quality and Testing | Every domain behavior (each stage and each gate) ships with an automated test; domtrack-import and crawl4ai-import tests lock SC-020, and resilience/budget tests lock the waiting and dead-letter behavior (FR-048, FR-052). | PASS |
| IX. Data Retention | Traces, table classifications, extracted plan records, replay runs, and alerts are retained for auditing (artifacts in object storage, metadata in Postgres); links are never hard-deleted (removal is a recorded state); traces remain the evidence for published data. | PASS |
| X. Crawling Ethics | Adaptive crawling and the refilter fetch honor robots.txt, use a transparent user-agent with contact URL, and apply per-domain rate limiting; the deterministic deny list excludes non-content resources. | PASS |
| XI. Authentication | Operator console reuses the existing JWT auth; every endpoint is operator gated (`ops` group or admin, `is_operator()`) and refuses owner access to decisions (FR-005). | PASS |
| XII. Prefer Established Libraries and Generators | `startapp` scaffolds `admin_console` and `notifications`; domtrack is used as-is (no reimplementation), crawl4ai provides adaptive crawling, and the LLM stages use an OpenAI-compatible client; `django-storages`/`boto3` provide S3 artifacts instead of hand-written storage code; constance, guardian, and DRF are established libraries. | PASS |
| XIII. Configurable Values | All tunables are django-constance constants except the LLM token budget (model-backed per Principle II) and environment-specific values (settings/env): the artifact storage backend, S3 endpoint/credentials, the LLM gateway base URL/key, and the crawl query and bounds; no hard-coded thresholds or inline storage config. | PASS |

**Post-Phase 1 re-check**: PASS. Revised Phase 1 design keeps the module boundaries strict:
`admin_console` writes published records only through `catalog/interfaces.py` and emits
notifications only through `notifications/interfaces.py`, so `catalog` and `notifications`
remain independently owned and reusable (Principle V). The artifact layer is delegated to
Django's `STORAGES` API with an S3 default configurable from settings (Principle XII, XIII), and
the LLM-token-budget gate is a single checked boundary rather than new complexity. Complexity
Tracking remains empty.

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
    │   │                          #   django-storages, env-configurable); LLM gateway base URL;
    │   │                          #   crawl query/bounds; email backend
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
    │   │                          #   ExtractedTableColumn, ExtractedTableRow,
    │   │                          #   TableClassification, PlanRecord, SemanticLabel,
    │   │                          #   ReplayRun, LlmCostLedger + LLM token budget
    │   ├── interfaces.py          # the only sanctioned entry point for other modules
    │   ├── domtrack_client.py     # ONLY module that imports domtrack (FR-000, SC-020):
    │   │                          #   server-side adapters (headless capture, replay/compare,
    │   │                          #   tables extract/label)
    │   ├── artifacts.py           # Django STORAGES-backed artifact store (S3 default);
    │   │                          #   uuid-keyed writes/reads/deletes, never touches Postgres
    │   ├── plan_schema.py         # code-defined plan schema (Pydantic models) with plan-type
    │   │                          #   dimension (FR-027)
    │   ├── discovery.py           # crawl4ai adaptive crawling (statistical) + deterministic
    │   │                          #   link policy; ONLY module importing crawl4ai
    │   ├── refilter.py            # deterministic h1-h3/important-section extraction + LLM
    │   │                          #   plans-page refilter (FR-012..FR-015)
    │   ├── llm.py                 # OpenAI-compatible client; classification + schema extraction
    │   │                          #   with the token-budget gate + awaiting-budget state
    │   ├── services.py            # approvals (via interface), onboarding/discovery, refilter,
    │   │                          #   capture session, extraction, classification, plan
    │   │                          #   extraction, publish (via catalog interface), replay
    │   │                          #   orchestration, alerting (via notifications interface)
    │   ├── tasks.py               # django.tasks task functions (extract, label, replay link)
    │   ├── selectors.py           # console reads (queue, site detail, tables, plans, runs)
    │   ├── serializers.py         # DRF I/O + Pydantic boundary schemas
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
    │       ├── test_link_discovery.py       # adaptive crawl (stubbed) + deterministic policy
    │       ├── test_link_refilter.py        # input shape + recall-biased keep/drop
    │       ├── test_capture_flow.py         # headless server capture state machine
    │       ├── test_extraction.py
    │       ├── test_classification.py
    │       ├── test_plan_extraction.py      # schema-shaped data, no recipes
    │       ├── test_labeling_gate.py
    │       ├── test_artifact_storage.py     # STORAGES-backed, uuid keys, no DB blobs
    │       ├── test_publishing.py           # written via catalog interface + provenance
    │       ├── test_replay_diff.py          # content vs structural + conditional re-extract
    │       ├── test_budget_gating.py        # awaiting-budget queue + no double charge
    │       ├── test_resilience.py           # isolation, retry/backoff, dead-letter
    │       ├── test_failure_alerts.py       # alerting via notifications interface
    │       ├── test_domtrack_reuse.py       # domtrack only in client; crawl4ai only in discovery
    │       └── test_log_masking.py
    └── manage.py

frontend/
├── app/
│   └── ops/                       # NEW role-gated operator console (NOT /admin)
│       ├── layout.tsx             # operator guard + console shell
│       ├── page.tsx               # approvals queue
│       ├── companies/[companyId]/page.tsx
│       ├── sites/[siteId]/page.tsx            # site detail + pipeline stage
│       ├── sites/[siteId]/links/page.tsx      # link/refilter review
│       ├── links/[linkId]/tables/page.tsx     # extracted tables + classifications
│       ├── links/[linkId]/plans/page.tsx      # extracted plan data
│       ├── replay/page.tsx                    # replay runs + failure alerts
│       └── settings/page.tsx                  # labeling toggle, recipients, tunables
└── src/
    ├── features/
    │   └── ops/                   # NEW feature slices (approvals, links, tables,
    │       │                      #   plans, replay, settings)
    └── lib/
        ├── api/ops.ts             # console API client (follows api/companies.ts pattern)
        └── i18n/                  # Persian/RTL copy additions

specs/003-admin-ops-console/       # this feature's design artifacts
```

**Structure Decision**: Three module boundaries, each justified by ownership rather than
convenience:

- **`admin_console` (new)** owns the site-maintenance pipeline (Site, Link, CaptureSession,
  Trace metadata, extracted tables, classifications, plan records, labels, replay runs, cost
  ledger + token budget), the
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
or reads like Django's built-in `/admin/`, and the console API is mounted at `/api/v1/ops/`. The
console exposes the automated pipeline's state (discovered/refiltered links, tables and their
classifications, extracted plan data, replay changes, budget) and the controls (the LLM token
budget and thresholds); operators no longer map or clean data by hand.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations. Table intentionally empty.
