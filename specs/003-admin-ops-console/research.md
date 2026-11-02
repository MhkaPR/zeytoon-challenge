# Phase 0 Research: Admin Console — Company Approval & Site Data Maintenance

All Technical Context unknowns are resolved below. Each entry records the decision, why it
was chosen, and what alternatives were considered. No `NEEDS CLARIFICATION` items remain.

The feature is a pipeline with ten stages. Approval and publishing are platform work; the
ingestion stages orchestrate the mandated `domtrack` library plus `crawl4ai`, with an LLM
layer for the link refilter, table classification, and plan-schema extraction. The research
therefore concentrates on (a) where the console lives, (b) how background work is scheduled
without Celery, (c) how each domtrack/crawl4ai capability is reached, and (d) the platform
models that hold the pipeline's state between stages.

## R1. Admin console placement and module boundary

- **Decision**: Build the operator console inside this feature as a
  **new backend Django app `admin_console`** (`python manage.py startapp admin_console`)
  that owns every site-maintenance entity (Site, Link, Trace, ExtractedTable,
  TableClassification, PlanRecord, SemanticLabel, ReplayRun, ChangeRecord, FailureAlert,
  LlmCostLedger) and the approval *queue* surface. Company verification itself is **not**
  re-implemented: the console calls
  `companies.interfaces.CompaniesInterface` →
  `companies.services.record_verification_decision`, which already exists from feature 002.
  The frontend grows an `frontend/app/ops/**` route group with
  `frontend/src/features/ops/**` slices and the console API is mounted at `/api/v1/ops/`.
  The route segment is deliberately **not** `admin`: a Next.js `/admin` path would shadow
  and read like Django's built-in `/admin/` site, which is a different (framework) surface,
  so the operator console uses `/ops`.
  Two adjacent concerns are owned elsewhere and are **not** in `admin_console`: published
  plan records (owned by `catalog`, R13) and notifications (owned by a new `notifications`
  app, R15).
- **Rationale**: The spec's assumptions state that this feature *is* the operator console
  that feature 002 modeled as an external application; feature 002 explicitly deferred the
  duplicate-detection and approval surface to "the admin panel". A dedicated app keeps 46
  FRs of pipeline state out of `companies` (which is already feature-complete) while
  respecting Principle V — the console consumes companies only through
  `companies/interfaces.py`. There is no second owner of `VerificationDecision`, so
  SC-001 (exactly one append-only record per decision) stays structurally true.
- **Alternatives considered**: (a) Extending the `companies` app — rejected: it would
  co-locate two features' concerns and force `admin_console` work into `companies`' test
  suite and migrations; (b) the scaffolded empty `panel` app — rejected: `panel` is the
  company-owner surface name from 002 and is unrelated; (c) a separate deployable admin
  application — rejected: violates Principle V (no microservices) and the single-deployable
  model.

## R2. Background work: Django 6 Tasks + a scheduling management command (no Celery)

- **Decision**: Use **Django 6's built-in Tasks framework** (`django.tasks`) for all
  asynchronous/job-style work, configured via the `TASKS` setting. Configure an explicit
  alias so a future Redis-backed deferred backend can be dropped in without changing call
  sites, and default to `django.tasks.backends.immediate.ImmediateBackend` for development
  and tests (with `django.tasks.backends.dummy.DummyBackend` available for tests that must
  assert enqueueing only). Periodic replay is **not** handled by a task backend: it is
  driven by a **custom management command**
  (`python manage.py run_scheduled_replays`), run by the deployment scheduler (cron /
  systemd timer / container sidecar), which scans for due `ReplayRun`s and then enqueues a
  `django.tasks` task per due link. **Celery is not used anywhere.**
- **Rationale**: The user's instruction is explicit ("use django 6 tasks no celery"), and
  Principle XII prefers framework-provided mechanisms. Django 6.1.2 ships `django.tasks`
  with `ImmediateBackend` and `DummyBackend` only — no Redis/database *deferred* backend is
  bundled, and `run_after`/priority are backend-dependent (`supports_defer`,
  `supports_priority`). A management command is the idiomatic, framework-native way to
  provide the "every configured period" trigger (FR-037) because the period is a runtime
  constant, not a cron expression the app controls; the command computes due runs and
  enqueues them, so the schedule stays database-driven and independently testable. Long
  per-link replay/compare/diff then runs as a task so the scheduler loop stays short.
- **Alternatives considered**: (a) Celery/Celery Beat — rejected by explicit user
  instruction; (b) `django-crontab`/`django-q2` — rejected: adds a dependency the framework
  already covers, and `django-q2` reintroduces a Celery-like broker; (c) a long-running
  in-process `runserver`-side scheduler thread — rejected: does not survive multiple
  workers and is not testable; (d) relying on `run_after` — rejected: unsupported by the
  bundled backends, so a command-driven trigger is required regardless.

## R3. How each pipeline stage reaches domtrack

- **Decision**: Reach every domtrack capability **server-side through the Python library**,
  in one thin adapter module `admin_console/domtrack_client.py` (the **only** file that
  imports domtrack): `domtrack.capture` (headless, fixed duration), `.replay` (`--record`),
  `.compare` (replay + record + diff), `.diff`, `.html`, `.tables` (extract), and
  `.tables.labeling`. Link discovery is a parallel server-side adapter
  (`admin_console/discovery.py`, the only file importing `crawl4ai`), and the refilter/
  classification/schema-extraction LLM calls go through `admin_console/llm.py`. No
  operator-machine domtrack instance exists (FR-000c).
- **Rationale**: Capture is now headless and server-side (FR-016), so the operator-local
  REST route is gone; running the library in-process avoids a second long-lived service and
  gives direct access to typed results (`CompareResult`, `DiffResult`, table dicts).
  Concentrating each third-party import in one adapter makes FR-000/SC-020 auditable (an
  import test asserts domtrack is imported only in the client and crawl4ai only in the
  discovery module).
- **Alternatives considered**: (a) Running `domtrack serve` and calling it over HTTP —
  rejected: an extra service and failure mode for no benefit when the library runs
  in-process; (b) shelling out to the `domtrack` CLI — rejected: brittle string parsing where
  the library exposes typed return values; (c) vendoring/forking domtrack — rejected by
  FR-000 ("used as-is").

## R4. Stored trace artifact and storage model

- **Decision**: Store the trace as a **file artifact in object storage** through Django's
  `STORAGES` API (`django-storages`), with **S3-compatible storage as the default backend**
  and the backend selectable per environment from settings (S3, local filesystem, or any
  other configured `STORAGES` alias) without code changes. The object key is
  **UUID-based** (`traces/<uuid4>.json`) so every artifact gets a unique, non-guessable,
  collision-free name independent of the operator's original path or the numeric trace id;
  the pipeline tree is not encoded in the key. A `Trace` row records: link, capture time,
  **storage key**, the **backend alias**, byte size, a content hash, and the capture duration
  (capture is always server-side and headless). The trace is **never
  converted** — the same object is what replay, compare, diff, and table extraction read
  (FR-000a). The database stores keys, not blobs.
- **Rationale**: The user requires artifacts to be saved in S3 by default while letting a
  developer or devops switch the storage type from settings — Django's `STORAGES` API with
  `django-storages` is exactly that indirection, so `admin_console` never writes filesystem
  or S3 code itself and the deployment keeps an Iran-hosted S3-compatible endpoint
  (Principle IV). UUID keys satisfy the requirement that the stored filename be unique and
  decoupled from the operator's local path; because the key is opaque and the row is the
  only mapping back to the link, a re-upload or a re-capture can never overwrite another
  trace (the hash still detects duplicate content for SC-008).
- **Alternatives considered**: (a) Storing the trace JSON in a Postgres `JSONField` —
  rejected: rrweb traces are large and would bloat Postgres and slow trace-adjacent
  queries; (b) a plain local media root — rejected by the explicit S3 requirement and
  because it pins storage to one host; (c) naming objects after the
  original path or `<link_id>/<trace_id>` — rejected: non-unique across re-captures, leaks
  host paths, and makes the key guessable; (d) normalizing the trace into platform tables —
  rejected: directly violates FR-000/FR-000a.

## R5. Link discovery: crawl4ai adaptive crawling (statistical) + deterministic policy

- **Decision**: Discover candidate links in `admin_console/discovery.py` (the only module
  importing `crawl4ai`) by running
  `AdaptiveCrawler(AdaptiveConfig(strategy="statistical", max_pages=…, max_depth=…,
  top_k_links=…)).digest(seed=site.domain, query=LINK_CRAWL_QUERY_*)` with a Persian and an
  English pass, then union the same-host internal links harvested from the crawled pages and
  reduce them with a deterministic policy: same-host only, fragment and query stripped, a
  configurable extension/segment deny list applied, and dedupe by normalized URL hash. No
  sitemap is fetched, parsed, or required (FR-008). The statistical strategy uses
  keyword/BM25 statistics only — no embeddings and no LLM.
- **Rationale**: The user requires adaptive crawling via the statistical strategy to replace
  sitemap discovery and to bias for recall, so the crawler's early-stop is pushed out
  (`confidence_threshold` high) and `max_pages`/`top_k_links` are the real recall bounds.
  The deterministic policy keeps discovery deterministic and cheap, and excludes non-content
  resources (scripts, styles, text, JSON/XML, documents, media, fonts, blog/docs/auth/cart/
  legal paths) before any refilter or capture cost is paid. Robots.txt, a transparent UA, and
  per-domain rate limiting are honored (Principle X).
- **Alternatives considered**: (a) sitemap.xml parsing (the original design) — rejected by
  the user; (b) adaptive crawling with the embedding strategy — rejected: embeddings need a
  model and cost, and the user requires statistics only; (c) a plain BFS crawl — rejected:
  adaptive ranking focuses the crawl on plans pages without an LLM.

## R6. Site and Link state model

- **Decision**: `Site` is one-per-company (FR-007), created when the company is approved,
  keyed by the company's normalized domain, and carries `maintenance_state`
  (`onboarding` → `active` → `suspended`). `Link` carries `review_state`
  (`candidate` / `kept` / `removed`), a `pipeline_stage`
  (`review` → `capture` → `extracted` → `mapped` → `cleaned` → `published`, plus `flagged`
  and `failed`), the current trace reference, and an `is_active` flag used by replay.
  Removal is recorded as a transition to `removed`, never a delete (FR-010), so the
  removed set stays auditable and re-onboarding is idempotent.
- **Rationale**: FR-007's "one site per company" is a structural rule, best expressed as a
  uniqueness constraint on `Site.company`; FR-010's "removed links are recorded as
  removed" needs a state, not a delete; and the pipeline stage on the Link is what every
  gate (FR-014, FR-020, FR-030) can check without re-deriving it.
- **Alternatives considered**: (a) A separate `SiteLink` join table — rejected: links
  belong to exactly one site, so an FK is simpler; (b) representing link removal as a
  boolean `excluded` — rejected: a two-valued flag cannot express the review→capture
  progression alongside removal; (c) hard-deleting removed links — rejected by FR-010.

## R7. Server-side headless capture

- **Decision**: Model capture as a short-lived `CaptureSession` row (`pending` → `recording`
  → `stored` / `failed`) driven entirely on the server: the pipeline calls
  `domtrack_client.capture_headless(url, duration_ms, nav_timeout_ms)`, which opens the link
  in a headless browser, waits for the page to settle (`networkidle`), scrolls to the bottom
  to trigger lazily loaded content, records for the configured fixed duration (headless
  requires a fixed duration), and stores the resulting trace through `artifacts.save_trace`.
  There is no operator field, no local path, and no upload step; a capture that produces no
  trace marks the session `failed` and leaves the link at `captured` (FR-016..FR-019).
- **Rationale**: The user requires capture to run on the server, not on a client machine;
  headless mode requires a fixed `duration_ms`, which the pipeline supplies from constance.
  The explicit state machine is what enforces FR-018 ("MUST NOT advance until a trace has
  been stored") and makes repeated attempts auditable.
- **Alternatives considered**: (a) interactive operator capture (the original design) —
  rejected by the user; (b) a single fire-and-forget call with no session — rejected: it
  cannot distinguish a failure from a stored trace, and the edge cases require a recorded
  failed attempt; (c) a per-site interaction recipe for tabs/accordions — deferred: headless
  v1 captures the loaded state and flags interaction-dependent links.

## R8. Extraction persistence shape

- **Decision**: Call `domtrack.tables.discover_tables(raw, DiscoveryConfig(...))` in
  server-side; persist one `ExtractedTable` row per returned table (with its
  `parent`/`meta`/`score` and `column_count`/`row_count`) and one `ExtractedTableColumn`
  row per column (id, label, `path`/selector, `atype`, `slot`, `coverage`,
  `row_count`), plus the table's rows as `ExtractedTableRow` rows keyed by column id.
  Store the domtrack discovery `score` so the operator can see which candidate was chosen.
  Extraction is idempotent per trace: re-running replaces the existing extraction for that
  trace in a transaction, so "same trace → same tables" (SC-010) holds as data, not just
  as library behavior. When domtrack returns zero tables, the link is flagged (FR-022).
- **Rationale**: FR-020 requires storing columns and rows *with each column's path and
  coverage as domtrack reports them*; the column `path` is kept as provenance and as the
  identifier classification and replay change-matching attach to (FR-025). Normalizing
  columns into rows keeps classification and change-detection queries simple without parsing
  a JSON blob in Python, and the replace-in-transaction rule
  makes determinism a queryable property.
- **Alternatives considered**: (a) Storing the raw domtrack table dict as JSON only —
  rejected: the per-table classification and replay change matching need queryable table and
  column records; (b) storing rows as a single JSON blob per table — considered for large
  tables; rejected for the initial `tasks.md` scope because relational rows keep
  classification, change detection, and provenance queries simple, and may be revisited as a
  performance task if row counts demand it; (c) re-extracting lazily on every read —
  rejected: violates FR-020's "store the returned tables" and SC-010.

## R9. Labeling gate and the LLM token budget

- **Decision**: Labeling runs only when the constance toggle `LABELING_ENABLED` is true
  (default **false**, FR-032). When on, the server calls
  `domtrack.tables.labeling.label_tables(data, LabelConfig(provider, model, base_url, lang,
  batch_size, dry_run))` using provider/model/language/batch-size from constance and the API
  key from the environment (Principle III). Every LLM-gated call (refilter, classification,
  schema extraction, labeling) first checks the **admin-set LLM token budget** held in a
  Django model (`LlmCostLedger`, model-backed per Principle II): when the pending call would
  exceed the budget for the period, the call is not made, the link enters
  `awaiting_llm_budget`, and the admin is notified; the rest of the pipeline continues
  (FR-047..FR-049). Spend rows are keyed by `idempotency_key` so a retry is not charged twice
  (FR-050). Labels are written to `SemanticLabel` rows; when labeling is disabled or
  budget-blocked, no label rows exist and every downstream stage behaves identically
  (FR-033, SC-019).
- **Rationale**: The toggle must be admin-controlled at runtime (Principle XIII) and the
  budget must be model-backed (Principle II). Because domtrack owns the labeling LLM call,
  the platform cannot meter inside it, so the adapter pre-checks the budget and records the
  call's spend after the fact — the cheapest enforceable point that keeps the budget
  authoritative and observable, and the queue/resume behavior keeps non-LLM stages moving.
- **Alternatives considered**: (a) Metering inside domtrack — rejected: domtrack is used
  as-is (FR-000) and is not modifiable; (b) enforcing the budget only after the call —
  rejected: FR-048 forbids exceeding it, not just detecting it; (c) making labeling a hard
  dependency of extraction — rejected by FR-033.

## R10. Table classification and plan-schema extraction (data, not recipes)

- **Decision**: After extraction, each `ExtractedTable` is classified by an LLM
  (`llm.classify_tables`) into `TableClassification` (plans/not-plans, plan type, confidence),
  then every plans table is extracted by an LLM (`llm.extract_plans`) into `PlanRecord` rows
  validated against the code plan schema (R11) — a list of plan dicts in the standard format,
  normalized by the model (amounts, units, billing periods). **No selectors and no formulas
  are produced or stored anywhere**: there is no operator mapping workspace, no
  `ExtractionRecipe`, and no formula engine (FR-028). A table whose extraction cannot fill the
  schema's required fields is skipped; the page's other mappable tables are still extracted.
  Re-extraction is idempotent for an unchanged table and runs on initial extraction and on a
  replay change that touches a plans table (FR-029, FR-031, FR-042).
- **Rationale**: The user requires the LLM to extract the *data* against a Pydantic schema,
  not to build a selector/formula recipe, and to skip tables that cannot map. A per-table
  classification is the anchor replay needs to decide whether a change is relevant (R14), and
  relational `PlanRecord` rows keep the published payload queryable and the required-field
  gate enforceable without a recipe.
- **Alternatives considered**: (a) the original operator mapping workspace with
  selector+formula recipes — rejected by the user (no operator, no formulas); (b) one flat
  JSON blob per page — rejected: a per-table classification must anchor replay change
  detection; (c) re-deriving the extraction on every read — rejected by
  idempotency/observability.

## R11. Plan schema representation

- **Decision**: Define the plan schema in **code** as a structured Pydantic module
  (`admin_console/plan_schema.py`): a top-level schema with a **plan-type dimension**
  (`hosting`, `cdn`, `virtual_server`, …), each plan type carrying an ordered set of field
  definitions (`key`, `label`, `type` (`number`/`text`/`bool`/`unit`/`enum`),
  `required`, `unit` family, `enum` values). It is read-only (never user-editable; edited by
  hand in code) and is the target the LLM extraction validates against. `PlanRecord.values`
  is keyed by `(plan_type, field_key)`, so the schema can grow new plan types without
  migrating records.
- **Rationale**: FR-027 requires a code-defined schema that is not user-editable and carries
  a plan-type dimension selecting which fields apply. A Pydantic module gives type
  checking/validation, unit declarations the LLM normalizes to (R12), and a stable key space
  for plan records.
- **Alternatives considered**: (a) A schema stored in the database — rejected by FR-027;
  (b) one flat schema without plan types — rejected: the spec explicitly requires the
  plan-type dimension; (c) Pydantic models for the schema — considered; the schema is
  metadata used by both backend and frontend, so a plain declarative structure (with a
  Pydantic validation of the extracted plan records against it) is chosen.

## R12. Value normalization lives in the LLM extraction (no cleaning engine)

- **Decision**: There is **no separate cleaning rule engine and no formula evaluation**.
  Normalizing amounts, units, and billing periods is part of the LLM schema extraction
  (`llm.extract_plans`, R10), which emits `PlanRecord.values` already in the units the plan
  schema declares (`unit_family`). The schema's `enum` values constrain category
  normalization, and the required-field check gates publishability. What the original design
  called "cleaning exceptions" no longer exists; a value the model cannot normalize means the
  table cannot fill a required field and is skipped (FR-030).
- **Rationale**: The user requires the LLM to produce the data directly with no formulas, so
  a separate deterministic cleaner would both duplicate the normalization and contradict the
  "data, not formulas" decision. Keeping normalization inside the validated schema extraction
  makes the normalized output the single artifact and removes an entire component.
- **Alternatives considered**: (a) the original constance-driven cleaning rules engine —
  rejected by the user; (b) normalizing at query time in the frontend — rejected: filters
  must work on stored, standardized values.

## R13. Publishing and provenance

- **Decision**: `PublishedRecord` **belongs to the `catalog` app**, not `admin_console`: the
  published plan data is what catalog and search consume, so its model, migration, and read
  surface live where they are used. The LLM plan extraction therefore produces a normalized,
  plan-typed payload that `admin_console` writes through `catalog/interfaces.py`
  (`catalog.services.upsert_published_record(...)` / `retire_published_record(...)`), which
  owns the upsert-by-`(site, link, natural key)` rule and preserves the provenance references
  to `site`, `link`, `trace`, and the plans-table `classification` (FR-037). When a replay
  reports an item removed (domtrack diff `removed`), a replay-report call through the same
  interface retires the record rather than retaining stale values (FR-038). (`site`, `link`,
  `trace`, and `classification` references cross modules as opaque ids, so `catalog` never
  imports `admin_console` internals.) This feature does not implement search or ranking
  (FR-057).
- **Rationale**: The user's requirement is that the model used by catalog and search must
  live in the proper app (no published-plan model inside the admin/ops module), and
  Principle V requires the writer to go through an interface rather than touching
  `catalog`'s tables. Putting `PublishedRecord` in `catalog` also makes the plan entity's
  home consistent with feature 002's statement that plans are owned outside the console.
- **Alternatives considered**: (a) A `PublishedRecord` model inside `admin_console` — rejected
  by the user's requirement (wrong owner) and it would force catalog/search to depend on the
  console; (b) `admin_console` writing `catalog` tables directly — rejected by Principle V;
  (c) soft-retaining removed records — rejected by FR-036.

## R14. Replay, diff, failure rate, and alerting

- **Decision**: A scheduled run (`ReplayRun`, one row per link per cycle) calls
  `domtrack.compare.compare_replay(before_path, ReplayConfig(mode="clean", …), recording=
  RecordingConfig(enabled=True, …))` — replay, record-during-replay, and diff in one call
  (FR-040) — then classifies each change as a **content change** or a **structural change**
  and records `ChangeRecord`s. When a change touches a region with a
  `TableClassification(is_plans_table=true)`, the run re-extracts plan data with the LLM
  (re-discovering and re-classifying first when the change is structural), and a change
  elsewhere triggers no LLM work (FR-041..FR-043); it then applies the resulting updates to
  published data and records `stats.failed`/`stats.failures`. The link's failure rate is
  derived from domtrack's reported failures over a configurable trailing window (constance),
  not computed from our own heuristics. When the rate crosses the configured threshold, a
  `FailureAlert` is raised once per crossing (state-based, so it is not re-raised every
  cycle while the condition persists — an explicit edge case) and notification is
  dispatched (R15). The operator can re-run the maintenance stages for the link (FR-046).
- **Rationale**: FR-038 mandates domtrack for replay *and* diff and forbids reimplementing
  them, so `compare_replay` is the single correct call. Making the alert state-based (tied
  to `FailureAlert.open`) rather than event-based satisfies the edge case "alert not
  repeated after the rate falls and rises again only on a new crossing".
- **Alternatives considered**: (a) Separate replay + diff calls — rejected: `compare_replay`
  already couples them and is the documented capability; (b) computing our own diff of
  extracted tables — rejected by FR-038; (c) event-only alerting — rejected: produces
  repeat alerts, contradicting the edge case.

## R15. Notifications (in-app only; email out of scope by project decision) and recipient list

- **Decision**: Build a **new general-purpose `notifications` app** that owns
  `Notification` (a generic, typed event with structured payload: `event_type`, severity,
  subject, body, related-object reference, dedup key), `NotificationRecipient`
  (admin-managed, add/remove — FR-041), and `NotificationDelivery` (one row per recipient ×
  channel with sent/read state). Channels are pluggable in `notifications/channels.py` — an
  in-app channel and an email channel through Django's configured email backend, with room
  for more without changing callers. Callers publish through
  `notifications/interfaces.py` (`notifications.notify(event_type, recipients, …)`); the app
  resolves recipients, fans out per channel, and dispatches deliveries from a `django.tasks`
  task so the caller (here, the replay run) is never blocked by SMTP. `admin_console`'s
  `FailureAlert` keeps only the **link-state** concern (which link needs updating, first
  raised, resolved) and raises a notification through the interface, so alerting logic and
  delivery logic stay separate.
- **Rationale**: The user requires notifications to be more general and to live in their own
  app rather than in the admin/ops module. A generic notification model + pluggable channels
  means other features (e.g. approval notices, provider degradation, LLM budget exhaustion notices —
  Principle II) reuse the same machinery without duplicating delivery, which is exactly the
  platform-capability shape Principle XII favors. Splitting "what is wrong" (link alert
  state) from "how it is delivered" (notification app) keeps each app's model set minimal.
- **Alternatives considered**: (a) Notifications modeled inside `admin_console` — rejected by
  the user's requirement and it would make every other feature import the console to notify;
  (b) `django.contrib.messages`/a third-party library — considered; `contrib.messages` is
  request-scoped and not persistent, and a third-party service is rejected by Principle IV
  (Iran-hosted) and dependency creep; (c) Email-only or WebSocket/SSE push — rejected by
  FR-041's "both in-app and by email" and because a persistent in-app inbox is verifiable
  without realtime infrastructure.

## R16. Runtime tunables (django-constance)

- **Decision**: Store all runtime-tunable values as constance constants (database backend),
  read through `constance.config`. Initial set:
  `REPLAY_PERIOD_HOURS`, `REPLAY_BATCH_SIZE`, `FAILURE_RATE_THRESHOLD`,
  `FAILURE_RATE_WINDOW_RUNS`, `LABELING_ENABLED`, `LABELING_PROVIDER`,
  `LABELING_MODEL`, `LABELING_LANGUAGE`, `LABELING_BATCH_SIZE`,
  `LINK_CRAWL_QUERY_FA`, `LINK_CRAWL_QUERY_EN`, `LINK_CRAWL_MAX_PAGES`,
  `LINK_CRAWL_MAX_DEPTH`, `LINK_CRAWL_TOP_K`, `LINK_DENY_EXTENSIONS`,
  `LINK_DENY_SEGMENTS`, `LINK_DISCOVERY_MAX_LINKS`, `REFILTER_PROVIDER`,
  `REFILTER_MODEL`, `REFILTER_DROP_CONFIDENCE`, `CAPTURE_FIXED_DURATION_MS`,
  `CAPTURE_NAV_TIMEOUT_MS`, `RETRY_MAX_ATTEMPTS`, `RETRY_BACKOFF_SECONDS`,
  `PUBLISH_AUTO_THRESHOLD`.
  The LLM **token budget** lives in a Django model (Principle II), not constance.
  Environment-specific values live in `settings.py` with env overrides and now include the
  **artifact storage backend**: `STORAGES["default"]` (defaulting to S3 via
  `django-storages`, overridable to local filesystem or another alias),
  `AWS_STORAGE_BUCKET_NAME`/`AWS_S3_ENDPOINT_URL`/`AWS_ACCESS_KEY_ID`/
  `AWS_SECRET_ACCESS_KEY`/`AWS_S3_REGION_NAME`, the LLM gateway base URL, the email backend,
  and request timeouts. Provider/LLM and S3 secrets remain environment-only (Principle III).
- **Rationale**: FR-054/SC-018 require every tunable to be changeable at runtime without
  editing code, and Principle XIII names constance (database backend) for exactly this;
  Principle II separately requires the budget in a model. Splitting by "operator-facing
  tunable vs environment vs domain-identity value" matches the constitution's own
  taxonomy.
- **Alternatives considered**: (a) All values in `settings.py` — rejected: not
  runtime-adjustable; (b) a bespoke settings model for everything — rejected: constance is
  the established, constitution-named tool and provides an operator UI; (c) putting the
  token budget in constance too — rejected: Principle II requires a model-backed budget rule.

## R17. Observability and masked logging

- **Decision**: Emit structured JSON events (reusing `utils.logging`) for: approval
  decisions (delegated to `companies.events`), site onboarded, links discovered/refiltered/
  dropped, capture started/succeeded/failed, trace stored, extraction completed/empty,
  classification completed, plan extraction completed/skipped, labeling run/skipped/
  budget-blocked (with token count and cost), published/removed, replay run completed with
  change kind and failure rate, budget exhausted, alert raised/resolved, and notification
  delivery. Metrics required by Principle VII are exported as event fields: crawl success
  rate per provider, latency per site, LLM call count and tokens, and replay staleness. Hot
  paths (per-link replay loops, per-table extraction) use aggregation/sampling rather than
  per-item logs; no log entry contains unmasked personal data (SC-021).
- **Rationale**: FR-055/FR-056 require these events and per-provider metrics, and
  Principles VII and the anti-noise rule require sampling on hot paths. Reusing the
  existing masking machinery satisfies SC-021 without a second implementation.
- **Alternatives considered**: (a) A metrics library (Prometheus client) — considered;
  deferred, since the constitution specifies structured JSON logs as the mechanism and no
  metrics backend is mandated; (b) per-row logging in extraction/replay — rejected by the
  anti-noise rule.

## R18. Frontend structure (no mapping spreadsheet)

- **Decision**: Add an **`ops`** route group in the Next.js App Router
  (`frontend/app/ops/**`: approval queue, site detail, links/refilter review, tables &
  classifications, plan data, replay & alerts, settings) with feature slices in
  `frontend/src/features/ops/**`, an API client module `frontend/src/lib/api/ops.ts`
  following the existing `lib/api/companies.ts` pattern, and Persian/RTL copy via
  `src/lib/i18n`. The console API is mounted at `/api/v1/ops/`. There is **no Handsontable
  grid and no mapping workspace**: the operator reviews auto-extracted plan data and manages
  the token budget/thresholds. `ops` routes are guarded by the operator role and kept in the
  same app (single deployable, Principle V).
- **Rationale**: The user requires that the frontend admin URL must not be `admin` like
  Django's `/admin`; `ops` is an unambiguous operator-console name that cannot be confused
  with Django's built-in admin site and leaves the framework admin convention untouched.
  Reusing the existing component/design system and i18n keeps the console consistent with the
  rest of the frontend (Principle XII); the route group is the idiomatic App-Router way to
  isolate a role-gated area without a second application.
- **Alternatives considered**: (a) `frontend/app/admin/**` — rejected by the user: it would
  shadow/read like Django's `/admin`; (b) a separate admin frontend application — rejected:
  contradicts single-deployable modular monolith (Principle V) and duplicates the design
  system; (c) a mapping spreadsheet (Handsontable) — rejected: mapping is retired, so no
  grid dependency is needed.

## R19. Access control for the console

- **Decision**: Every console endpoint requires an authenticated operator (`is_admin()`),
  enforced by an `AdminOnlyView` base in `admin_console/api.py` (mirroring the `companies`
  pattern). Company owners can never reach approval decisions (FR-005); site-maintenance
  endpoints are operator-only as well, since they act on behalf of approved companies.
  Capture runs headlessly on the server under the same operator role gate, so there is no
  operator-machine object-level permission to model.
- **Rationale**: FR-005 requires refusal of any owner attempt to influence their own
  verification, and the whole console is an operator surface; a single shared base class
  makes the rule uniform and auditable.
- **Alternatives considered**: (a) Reusing `companies.api.AdminOnlyView` — the two apps
  must not import each other's internals; a symmetric base in `admin_console` is cheaper
  than a cross-module import, though the role check itself reuses
  `accounts.selectors.user_from_request`/`User.is_admin()`; (b) django-guardian object
  permissions per company — rejected: the console is role-gated, not per-object.

## R20. Company rejection after maintenance started

- **Decision**: When a decision changes a company to `rejected`, the console sets its
  `Site.maintenance_state` to `suspended`; replay skips suspended sites, and any further
  publishing for them is blocked until the company is verified again (edge case in the
  spec). This is the single place where the two domains (companies status vs site
  maintenance) meet, and it goes through `CompaniesInterface` reads plus an admin-console
  write to its own `Site`.
- **Rationale**: The edge case requires suspension, not deletion or continued publishing;
  keeping the coupling in one documented spot preserves module boundaries (Principle V).
- **Alternatives considered**: (a) Continuing to publish until the data goes stale —
  rejected by the edge case; (b) deleting the site — rejected: the company may be
  re-approved and the pipeline state should survive.

## R21. Adaptive-crawl recall tuning

- **Decision**: Bias discovery toward recall, since a missed plans page is a lost provider.
  Use a high `confidence_threshold` (so the crawler does not stop early), a large
  `max_pages` as the real ceiling, a high `top_k_links` (the default of 3 is far too low to
  surface a provider's whole plans section), and a high `saturation_threshold`; run a
  Persian and an English query pass and union the results. The candidate set is bounded by
  `LINK_DISCOVERY_MAX_LINKS` and reduced by the deterministic policy (R5).
- **Rationale**: crawl4ai's statistical strategy stops as soon as its confidence reaches
  `confidence_threshold`; the default settings are optimized to *stop early*, which fights
  "find many links". Because scoring is BFS over the frontier, recall is governed by
  `max_pages`/`top_k_links` and the query's term coverage, not by a precision dial.
- **Alternatives considered**: (a) default adaptive settings — rejected: they stop early and
  miss pages; (b) a second precision pass — unnecessary, since the LLM refilter (R22) already
  removes non-plans pages downstream.

## R22. Refilter: deterministic extraction, then one LLM call

- **Decision**: For each candidate link, fetch the page, derive the summary deterministically
  (`refilter.important_section`: the largest text-density block inside `<main>`/`<article>`,
  with nav/footer/script stripped and a size cap, plus the `h1–h3` headings), and send only
  the URL + headings + section to the LLM. The prompt returns
  `{is_plans_page, plan_type, confidence}`. Recall bias: drop only when `is_plans_page=false`
  and `confidence >= REFILTER_DROP_CONFIDENCE`; otherwise keep and set `refilter_flag` when
  confidence is low.
- **Rationale**: The user requires the model never to see HTML and requires the "important
  section" to come from a deterministic algorithm; a recall-biased drop rule means a
  provider is never silently lost, and the flag routes borderline cases to operator review.
- **Alternatives considered**: (a) sending cleaned HTML or markdown to the model — rejected
  by the user; (b) dropping on low confidence — rejected: it loses providers; (c) skipping
  the refilter — rejected: it wastes capture and LLM budget on non-plans pages.

## R23. LLM token budget: queue and resume, never stall the cycle

- **Decision**: Every LLM-gated stage (refilter, classification, schema extraction, labeling)
  checks the model-backed token budget before calling the model. When the budget is exhausted,
  the stage does not run: the link's stage is recorded as `awaiting_llm_budget`, an admin
  notification is raised, and the cycle continues with all non-LLM work (crawl, fetch,
  capture, extraction, unchanged-table processing, publishing of already-extracted data). When
  the budget is restored, the parked work resumes from its recorded stage. Each logical call
  carries an `idempotency_key`, so a retry never double-charges the ledger.
- **Rationale**: The user requires that links which can continue do continue and only
  LLM-gated work waits; the budget is admin-set (price-sensitive) and must not be exceeded.
  Making the wait a link state (not a failure) keeps the cycle healthy and makes the queue
  observable.
- **Alternatives considered**: (a) failing the cycle on exhaustion — rejected by the user;
  (b) skipping the work permanently — rejected: it would silently drop providers; (c) an
  unbounded retry loop — rejected: it would hammer the provider and the budget.

## R24. Resilience and artifact ordering

- **Decision**: Process each link in isolation so one failure never aborts the cycle. Wrap
  network/crawl/fetch/capture/LLM calls in a bounded retry with exponential backoff
  (`RETRY_MAX_ATTEMPTS`, `RETRY_BACKOFF_SECONDS`); when the budget is spent, mark the link
  `dead_lettered` with `last_error` and stop retrying it. Artifacts are written to the object
  store **before** the `Trace` row is committed, and an orphaned object is compensated, so a
  `Trace` row never exists without its artifact (FR-053). Retries reuse the LLM
  `idempotency_key` (R23) so no side effect is duplicated.
- **Rationale**: The user requires resilience to network and other errors; per-link isolation
  plus a bounded retry/dead-letter path keeps a single bad link from poisoning the batch, and
  the write ordering closes the two-system consistency gap between object storage and
  Postgres.
- **Alternatives considered**: (a) failing the whole cycle on the first error — rejected:
  one bad link would block every other link; (b) unbounded retries — rejected: it would spin
  on permanently broken links and burn budget; (c) writing the `Trace` row before the object
  — rejected: it can leave a row pointing at a missing artifact.
