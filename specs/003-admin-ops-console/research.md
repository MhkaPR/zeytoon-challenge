# Phase 0 Research: Admin Console — Company Approval & Site Data Maintenance

All Technical Context unknowns are resolved below. Each entry records the decision, why it
was chosen, and what alternatives were considered. No `NEEDS CLARIFICATION` items remain.

The feature is a pipeline with eight stages. Two of them (approval, publishing) are pure
platform work; six are thin orchestration over the mandated `domtrack` library. The
research therefore concentrates on (a) where the console lives, (b) how background work is
scheduled without Celery, (c) how each domtrack capability is reached, and (d) the platform
models that hold the pipeline's state between stages.

## R1. Admin console placement and module boundary

- **Decision**: Build the operator console inside this feature as a
  **new backend Django app `admin_console`** (`python manage.py startapp admin_console`)
  that owns every site-maintenance entity (Site, Link, Trace, ExtractedTable, SemanticLabel,
  ExtractionRecipe, PublishedRecord, ReplayRun, FailureAlert, NotificationRecipient,
  CleaningRule) and the approval *queue* surface. Company verification itself is **not**
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

- **Decision**: Reach domtrack through **two routes, matched to where the work runs**:
  1. **Local operator machine → REST API** (`domtrack serve`, FastAPI): the site panel's
     capture button calls the operator's local domtrack `POST /capture`. The base URL
     (`DOMTRACK_LOCAL_API_URL`) and capture timeout are settings, because only the operator
     knows their host/port and the default 8000 collides with Django's dev server.
  2. **Server → Python library directly**: scheduled replay, record-during-replay, compare,
     diff, HTML rebuild, table extraction, and LLM labeling run in-process in
     `admin_console`'s domtrack adapter, importing `domtrack.capture` / `.replay` /
     `.compare` / `.diff` / `.html` / `.tables` / `.tables.labeling`.
  A single thin adapter module (`admin_console/domtrack_client.py`) is the **only** file
  that imports domtrack, so every call site is auditable against SC-017 ("0 capabilities
  reimplemented").
- **Rationale**: FR-012 requires capture to open a Chrome window *on the operator's
  machine*, which is only possible through the local REST API; FR-038 and the labeling/
  extraction stages run server-side, where the library avoids HTTP overhead, avoids a
  second long-lived service to operate, and gives direct access to typed results
  (`CompareResult`, `DiffResult`, table dicts). Concentrating the import in one adapter
  makes the FR-000/SC-017 guarantee testable (an import test can assert domtrack is
  imported only there).
- **Alternatives considered**: (a) Running `domtrack serve` on the server for everything —
  rejected: the operator-local capture requirement forces a local instance anyway, and a
  server-side HTTP hop adds a failure mode for no benefit; (b) shelling out to the
  `domtrack` CLI — rejected: brittle string parsing where the library exposes typed return
  values; (c) vendoring/forking domtrack — rejected by FR-000 ("used as-is").

## R4. Stored trace artifact and storage model

- **Decision**: Store the trace as a **file artifact in object storage** through Django's
  `STORAGES` API (`django-storages`), with **S3-compatible storage as the default backend**
  and the backend selectable per environment from settings (S3, local filesystem, or any
  other configured `STORAGES` alias) without code changes. The object key is
  **UUID-based** (`traces/<uuid4>.json`) so every artifact gets a unique, non-guessable,
  collision-free name independent of the operator's original path or the numeric trace id;
  the pipeline tree is not encoded in the key. A `Trace` row records: link, capturing
  operator, capture time, origin, the **storage key**, the **backend alias**, byte size, a
  content hash, and the capture mode (interactive/fixed-duration). The trace is **never
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

## R5. Sitemap discovery and robots.txt compliance

- **Decision**: Implement discovery in `admin_console/discovery.py` using only the Python
  standard library (`xml.etree.ElementTree`) plus `httpx` for fetching: fetch
  `/robots.txt`, read the `Sitemap:` directives, and fall back to `/sitemap.xml`; follow
  sitemap-index (`<sitemapindex>`) nesting up to a configurable depth; extract `<loc>`
  entries and normalize them to absolute URLs. Requests use the transparent project
  user-agent with a contact URL and honor the site's crawl delay (Principle X).
- **Rationale**: No sitemap library is currently a dependency, and a sitemap is a small,
  well-specified XML format where a library adds a dependency for very little behavior.
  `httpx` is already the intended HTTP client and `xml.etree` is stdlib, so no new
  dependency is introduced and the crawling-ethics rules (robots.txt, transparent UA,
  per-domain rate limit) can be enforced in one place.
- **Alternatives considered**: (a) `ultimate-sitemap-parser` / `sitemap-parser` —
  considered; rejected as a new dependency for a format the stdlib parses, though it
  remains a drop-in if discovery needs grow; (b) a full crawler library (Scrapy) —
  rejected: far beyond sitemap enumeration and would duplicate domtrack's role;
  (c) treating any site as sitemap-less — rejected: FR-008 requires automatic discovery
  when a sitemap exists.

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

## R7. Capture flow, automatic transfer, and manual fallback

- **Decision**: Model capture as a short-lived `CaptureSession` row
  (`pending` → `recording` → `awaiting_upload` → `stored` / `failed`). The panel calls our
  `POST /api/v1/ops/links/{id}/captures`, which calls the **local** domtrack
  `POST /capture` and returns the local trace path domtrack reports. The panel then
  attempts automatic transfer by posting the file to
  `POST /api/v1/ops/captures/{id}/trace` (multipart); when the browser cannot read the
  local file (or CORS/permission blocks it), the same endpoint accepts an
  operator-confirmed manual upload, and a third path lets the operator paste the local
  path for an operator-side helper to read. Any path that fails leaves the link at
  `capture` and records the failure (FR-015, FR-017, edge cases).
- **Rationale**: The spec's assumption pins "automatic upload if possible" to the browser
  reading the file and transferring it, with a manual fallback — a browser cannot silently
  read an arbitrary local path, so the session state machine must explicitly model
  "recording finished, trace not yet stored". That same state machine is what enforces
  FR-014 ("MUST NOT advance until a trace has been stored").
- **Alternatives considered**: (a) A single upload endpoint with no session — rejected: it
  cannot distinguish "operator cancelled" from "upload still pending", and the edge cases
  require a recorded failed attempt; (b) a native helper/desktop agent that reads the path
  — rejected as out of scope and a maintenance burden; (c) requiring manual upload only —
  rejected: FR-015 requires attempting automatic transfer first.

## R8. Extraction persistence shape

- **Decision**: Call `domtrack.tables.discover_tables(raw, DiscoveryConfig(...))` in
  server-side; persist one `ExtractedTable` row per returned table (with its
  `parent`/`meta`/`score` and `column_count`/`row_count`) and one `ExtractedTableColumn`
  row per column (id, label, `path`/selector, `atype`, `slot`, `coverage`,
  `row_count`), plus the table's rows as `ExtractedTableRow` rows keyed by column id.
  Store the domtrack discovery `score` so the operator can see which candidate was chosen.
  Extraction is idempotent per trace: re-running replaces the existing extraction for that
  trace in a transaction, so "same trace → same tables" (SC-008) holds as data, not just
  as library behavior. When domtrack returns zero tables, the link is flagged (FR-020).
- **Rationale**: FR-018 requires storing columns and rows *with each column's path and
  coverage as domtrack reports them*; the column `path` is exactly what the mapping recipe
  needs later (FR-028). Normalizing columns into rows lets the mapping workspace query
  selectors without parsing a JSON blob in Python, and the replace-in-transaction rule
  makes determinism a queryable property.
- **Alternatives considered**: (a) Storing the raw domtrack table dict as JSON only —
  rejected: the mapping workspace and recipe need queryable per-column selectors;
  (b) storing rows as a single JSON blob per table — considered for large tables; rejected
  for the initial `tasks.md` scope because normalized rows keep mapping and cleaning
  queries simple, and may be revisited as a performance task if row counts demand it;
  (c) re-extracting lazily on every mapping open — rejected: violates FR-018's "store the
  returned tables" and SC-008.

## R9. Labeling gate and LLM cost ceiling

- **Decision**: Labeling runs only when the constance toggle `LABELING_ENABLED` is true
  (default **false**, FR-021). When on, the server calls
  `domtrack.tables.labeling.label_tables(data, LabelConfig(provider, model, base_url, lang,
  batch_size, dry_run))` using provider/model/language/batch-size from constance and the
  API key from the environment (Principle III). Before each call the adapter checks the
  LLM cost ceiling held in a Django model (feature-level rule per Principle II): if the
  next call would exceed it, labeling **stops and reports**, and it never silently
  overspends (FR-024). Labels are written to `SemanticLabel` rows; when labeling is
  disabled or ceiling-blocked, no label rows exist and every downstream stage behaves
  identically (FR-023, SC-016).
- **Rationale**: The toggle must be admin-controlled at runtime (Principle XIII) and the
  ceiling must be model-backed (Principle II, which explicitly requires a Django model for
  the ceiling). Because domtrack owns the LLM call, the platform cannot meter inside it, so
  the adapter pre-checks the ceiling against the planned batch and records the call's
  cost after the fact — the cheapest enforceable point that keeps the ceiling authoritative
  and observable.
- **Alternatives considered**: (a) Metering inside domtrack — rejected: domtrack is used
  as-is (FR-000) and is not modifiable; (b) enforcing the ceiling only after the call —
  rejected: FR-024 forbids exceeding it, not just detecting it; (c) making labeling a
  hard dependency of extraction — rejected by FR-023.

## R10. Mapping workspace and the extraction recipe

- **Decision**: The workspace is an operator page that renders a link's extracted tables
  in **Handsontable** (grid) with a table dropdown, driven by admin-console endpoints that
  serve tables/columns/rows and accept a saved recipe. The recipe is stored as
  `ExtractionRecipe` (one per link, versioned by `version`) plus one `RecipeFieldBinding`
  per schema field: the target `schema_field_key`, the source `table` + `column` (whose
  domtrack `path` is the selector), and the combination `formula`. The formula syntax is
  **Excel/spreadsheet-compatible**: cell references (`A1`, `B7`, or named column ranges over
  the table's columns), spreadsheet operators and functions (`+ - * / ^`, `=`, parentheses,
  `SUM`, `MIN`, `MAX`, `AVERAGE`, `IF`, `ROUND`, `CONCATENATE`/`&`, `TEXT`, unit-suffix
  handling for `10GB`/`1 TB` style cells), and `,` as the argument separator so a saved
  formula is valid to paste into Excel/LibreOffice/Google Sheets. It is validated at the
  request boundary against a whitelisted function/operator set (no arbitrary code, no host
  access), and evaluated by a small deterministic evaluator over resolved column values. A
  link is `mapped` only when every **required**
  schema field for the selected plan type has a binding (FR-030); opening the workspace
  restores saved bindings (FR-031); replay evaluates the same bindings (FR-029).
- **Rationale**: FR-028 requires recording a source selector *and* a combination formula
  per field — a per-field binding row is the only shape that captures both and is
  queryable per field. The user requires formulas to be valid in Excel/spreadsheet systems,
  so the grammar targets spreadsheet syntax rather than a bespoke DSL: operators already
  know it, mapping work is copy-pasteable into a spreadsheet for verification, and the
  Handsontable grid can echo the same expression. Versioning the recipe lets a re-map keep
  history without breaking published provenance (FR-035).
- **Alternatives considered**: (a) Storing the recipe as one JSON blob on the Link —
  rejected: cannot enforce "every required field connected" or query "which fields use this
  selector"; (b) a bespoke formula DSL — rejected by the explicit Excel-compatibility
  requirement; (c) `eval`-ing formulas with Python — rejected: arbitrary-code execution and
  not spreadsheet-valid; (d) a full visual formula builder — deferred as gold-plating for
  the first cut, since a spreadsheet-valid expression covers host/server plan arithmetic;
  (e) mapping without a stored recipe and re-deriving on replay — rejected explicitly by
  FR-029.

## R11. Plan schema representation

- **Decision**: Define the plan schema in **code** as a structured Python module
  (`admin_console/plan_schema.py`): a top-level schema with a **plan-type dimension**
  (`hosting`, `cdn`, `virtual_server`, …), each plan type carrying an ordered set of field
  definitions (`key`, `label`, `type` (`number`/`text`/`bool`/`unit`/`enum`),
  `required`, `unit` family, `enum` values). It is read-only (never user-editable), exposed
  to the mapping workspace through an admin-console endpoint. Recipes reference fields by
  `(plan_type, field_key)`, so the same code schema can grow new plan types without
  migrating recipes.
- **Rationale**: FR-027 requires a code-defined schema that is not user-editable and
  carries a plan-type dimension selecting which fields apply. A code module gives type
  checking, unit declarations the cleaning stage can consume (R12), and a stable key space
  for bindings.
- **Alternatives considered**: (a) A schema stored in the database — rejected by FR-027;
  (b) one flat schema without plan types — rejected: the spec explicitly requires the
  plan-type dimension; (c) Pydantic models for the schema — considered; the schema is
  metadata used by both backend and frontend, so a plain declarative structure (with a
  Pydantic validation of the recipe against it) is chosen.

## R12. Cleaning rules engine

- **Decision**: Implement cleaning as a rules registry keyed by field/unit family, with the
  rule set and its thresholds stored in **constance** (FR-043): unit standardization
  (GB/TB↔numeric, currency separators, Mbps/Gbps), number/range parsing, category
  normalization (enum mapping), and required-field presence. The engine returns a cleaned
  value plus a per-value outcome (`clean` / `exception`); only exceptions are surfaced to
  the operator (FR-033), and a record with exceptions keeps everything else cleaned and
  remains publishable (edge case).
- **Rationale**: FR-032/FR-033 define cleaning as *automatic first, exceptions surfaced*,
  and FR-043 requires the rules be runtime-tunable. Constance-backed rules satisfy both
  and let operations adjust standardization without a redeploy; a per-value outcome is what
  makes "surface only exceptions" precise and testable.
- **Alternatives considered**: (a) Hard-coded cleaning functions — rejected by FR-043 and
  Principle XIII; (b) a third-party dataframe/cleaning library — rejected: the domain rules
  are format-specific and small, and a library would add a dependency without removing the
  rule-authoring work; (c) cleaning at query time in the frontend — rejected: filters must
  work on stored, standardized values.

## R13. Publishing and provenance

- **Decision**: `PublishedRecord` **belongs to the `catalog` app**, not `admin_console`: the
  published plan data is what catalog and search consume, so its model, migration, and read
  surface live where they are used. Cleaning therefore produces a cleaned, plan-typed
  payload that `admin_console` writes through `catalog/interfaces.py`
  (`catalog.services.upsert_published_record(...)` / `retire_published_record(...)`), which
  owns the upsert-by-`(site, link, natural key)` rule and preserves the provenance FKs to
  `site`, `link`, `trace`, and `recipe` version (FR-035). When a replay reports an item
  removed (domtrack diff `removed`), a replay-report call through the same interface retires
  the record rather than retaining stale values (FR-036). (`site`, `link`, `trace`, and
  `recipe` references cross modules as opaque ids, so `catalog` never imports
  `admin_console` internals.) This feature does not implement search or ranking (FR-046).
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
  (FR-038) — then applies the resulting `diff` (added/removed/changed) to published data
  (FR-039) and records `stats.failed`/`stats.failures`. The link's failure rate is derived
  from domtrack's reported failures over a configurable trailing window (constance), not
  computed from our own heuristics. When the rate crosses the configured threshold, a
  `FailureAlert` is raised once per crossing (state-based, so it is not re-raised every
  cycle while the condition persists — an explicit edge case) and notification is
  dispatched (R15). The operator can re-run all stages for the link (FR-042).
- **Rationale**: FR-038 mandates domtrack for replay *and* diff and forbids reimplementing
  them, so `compare_replay` is the single correct call. Making the alert state-based (tied
  to `FailureAlert.open`) rather than event-based satisfies the edge case "alert not
  repeated after the rate falls and rises again only on a new crossing".
- **Alternatives considered**: (a) Separate replay + diff calls — rejected: `compare_replay`
  already couples them and is the documented capability; (b) computing our own diff of
  extracted tables — rejected by FR-038; (c) event-only alerting — rejected: produces
  repeat alerts, contradicting the edge case.

## R15. Notifications (in-app + email) and recipient list

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
  means other features (e.g. approval notices, provider degradation, LLM ceiling breaches —
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
  `SITEMAP_FETCH_TIMEOUT_SECONDS`, `SITEMAP_MAX_INDEX_DEPTH`,
  `LINK_DISCOVERY_MAX_LINKS`, `CLEANING_RULES`, `CLEANING_UNIT_FAMILIES`,
  `CAPTURE_MODES_ALLOWED`, `PUBLISH_AUTO_THRESHOLD`,
  `ALERT_RECIPIENT_DEFAULT_EMAILS`.
  The LLM **cost ceiling** lives in a Django model (Principle II), not constance.
  Environment-specific values live in `settings.py` with env overrides and now include the
  **artifact storage backend**: `STORAGES["default"]` (defaulting to S3 via
  `django-storages`, overridable to local filesystem or another alias),
  `AWS_STORAGE_BUCKET_NAME`/`AWS_S3_ENDPOINT_URL`/`AWS_ACCESS_KEY_ID`/
  `AWS_SECRET_ACCESS_KEY`/`AWS_S3_REGION_NAME`, `DOMTRACK_LOCAL_API_URL`, the email backend,
  and request timeouts. Provider/LLM and S3 secrets remain environment-only (Principle III).
- **Rationale**: FR-043/SC-015 require every tunable to be changeable at runtime without
  editing code, and Principle XIII names constance (database backend) for exactly this;
  Principle II separately requires the ceiling in a model. Splitting by "operator-facing
  tunable vs environment vs domain-identity value" matches the constitution's own
  taxonomy.
- **Alternatives considered**: (a) All values in `settings.py` — rejected: not
  runtime-adjustable; (b) a bespoke settings model for everything — rejected: constance is
  the established, constitution-named tool and provides an operator UI; (c) putting the
  ceiling in constance too — rejected: Principle II requires a model-backed ceiling rule.

## R17. Observability and masked logging

- **Decision**: Emit structured JSON events (reusing `utils.logging`) for: approval
  decisions (delegated to `companies.events`), site onboarded, links discovered/entered/
  removed, capture started/succeeded/failed, trace stored, extraction completed/empty,
  labeling run/skipped/ceiling-blocked (with call count and cost), recipe saved/mapped,
  cleaning completed/exception, published/removed, replay run completed with failure rate,
  alert raised/resolved, and notification delivery. Metrics required by Principle VII are
  exported as event fields: crawl success rate per provider, latency per site, LLM call
  count and cost, and replay staleness. Hot paths (per-link replay loops, per-row cleaning)
  use aggregation/sampling rather than per-item logs; no log entry contains unmasked
  personal data (SC-018).
- **Rationale**: FR-044/FR-045 require these events and per-provider metrics, and
  Principles VII and the anti-noise rule require sampling on hot paths. Reusing the
  existing masking machinery satisfies SC-018 without a second implementation.
- **Alternatives considered**: (a) A metrics library (Prometheus client) — considered;
  deferred, since the constitution specifies structured JSON logs as the mechanism and no
  metrics backend is mandated; (b) per-row logging in cleaning/replay — rejected by the
  anti-noise rule.

## R18. Frontend structure and the Handsontable dependency

- **Decision**: Add an **`ops`** route group in the Next.js App Router
  (`frontend/app/ops/**`: approval queue, site detail, links review, capture, tables,
  mapping workspace, cleaning/publish, replay & alerts, settings) with feature slices in
  `frontend/src/features/ops/**`, an API client module `frontend/src/lib/api/ops.ts`
  following the existing `lib/api/companies.ts` pattern, and Persian/RTL copy via
  `src/lib/i18n`. The console API is mounted at `/api/v1/ops/`. The grid uses
  **Handsontable**, added as `@handsontable/react-wrapper` (+ `handsontable`), because the
  spec names Handsontable explicitly for the mapping spreadsheet (FR/User Story 6); the
  mapping formula cells use the Excel/spreadsheet-compatible grammar from R10. `ops` routes
  are guarded by the operator role and kept in the same app (single deployable, Principle V).
- **Rationale**: The user requires that the frontend admin URL must not be `admin` like
  Django's `/admin`; `ops` is an unambiguous operator-console name that cannot be confused
  with Django's built-in admin site and leaves the framework admin convention untouched.
  Reusing the existing component/design system and i18n keeps the console consistent with the
  rest of the frontend (Principle XII); the route group is the idiomatic App-Router way to
  isolate a role-gated area without a second application. Handsontable is specified by the
  user, so it is a deliberate, justified dependency (Principle XII's "unless justified"
  clause — here the user requires it).
- **Alternatives considered**: (a) `frontend/app/admin/**` — rejected by the user: it would
  shadow/read like Django's `/admin`; (b) a separate admin frontend application — rejected:
  contradicts single-deployable modular monolith (Principle V) and duplicates the design
  system; (c) building a custom grid — rejected: the user explicitly requires Handsontable
  and it is the established library for this exact use case; (d) TanStack Table/AG Grid —
  rejected: would contradict the explicit requirement.

## R19. Access control for the console

- **Decision**: Every console endpoint requires an authenticated operator (`is_admin()`),
  enforced by an `AdminOnlyView` base in `admin_console/api.py` (mirroring the `companies`
  pattern). Company owners can never reach approval decisions (FR-005); site-maintenance
  endpoints are operator-only as well, since they act on behalf of approved companies.
  Object-level permission for the local domtrack capture call is the operator's own machine
  and thus inherently operator-scoped.
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
