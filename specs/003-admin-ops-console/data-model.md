# Data Model: Admin Console — Company Approval & Automated Site Data Pipeline

Entities extracted from [spec.md](./spec.md) Key Entities and Functional Requirements.
All persistent domain models inherit `utils.models.TimestampedModel` (audit timestamps).
Field types are indicative; exact column types follow Django conventions. Ownership by app:

- `admin_console` (new): Site, Link, CaptureSession, Trace metadata, ExtractedTable /
  Column / Row, TableClassification, PlanRecord, SemanticLabel, ReplayRun / ChangeRecord,
  FailureAlert, and LlmCostLedger (the LLM token budget and spend).
- `catalog` (existing, extended): `PublishedRecord` — published plan data consumed by catalog
  and search, written by `admin_console` only through `catalog/interfaces.py`.
- `notifications` (new): `Notification`, `NotificationRecipient`, `NotificationDelivery`.
- `companies` (existing, referenced): `Company` and the append-only `VerificationDecision`.

Ownership note: company verification is **not** re-modelled. `admin_console` calls
`companies.interfaces.CompaniesInterface.record_verification_decision(...)`; the
append-only `companies.VerificationDecision` remains the single decision record (FR-002,
FR-006, SC-001).

## Entity Index

| Entity | Owner | Source FRs |
|--------|-------|------------|
| Company / VerificationDecision | `companies` (referenced) | FR-001..FR-006 |
| Site | `admin_console` | FR-007, FR-008, FR-011 |
| Link | `admin_console` | FR-009..FR-015, FR-018 |
| CaptureSession | `admin_console` | FR-016..FR-019 |
| Trace | `admin_console` | FR-019, FR-000a |
| ExtractedTable / Column / Row | `admin_console` | FR-020..FR-022 |
| TableClassification | `admin_console` | FR-023..FR-025 |
| PlanRecord | `admin_console` | FR-026..FR-031 |
| SemanticLabel | `admin_console` | FR-032..FR-035 |
| PlanSchema (code) | `admin_console` (code) | FR-027 |
| PublishedRecord | `catalog` | FR-036..FR-038 |
| ReplayRun / ChangeRecord | `admin_console` | FR-039..FR-043 |
| FailureAlert | `admin_console` | FR-044 |
| Notification / NotificationRecipient / NotificationDelivery | `notifications` | FR-045 |
| LlmCostLedger / LLM token budget | `admin_console` | FR-047..FR-050 (Principle II) |

## Site

The single crawl target for an approved company, identified by the company's registered
domain (FR-007). Created when a company is approved and its maintenance lifecycle starts.
The domain is the seed for adaptive crawling; there is no sitemap state.

| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | Primary key. |
| company | OneToOneField → `companies.Company` | **One site per company** (FR-007); uniqueness enforced at the DB. Referenced through the interface, not joined on in other modules. |
| domain | CharField (indexed) | Normalized company domain, copied from the company at onboarding; the adaptive-crawl seed (FR-008). |
| crawl_query | CharField (blank) | The host/server-plans query used for the site's discovery pass (constance default; override for edge sites). |
| maintenance_state | CharField choices | `onboarding` / `active` / `suspended` (FR-003, FR-011, edge case: rejection suspends). |
| onboarded_at | DateTimeField (null) | When onboarding completed. |
| last_replay_at | DateTimeField (null) | Set on each replay cycle; drives staleness (FR-039, SC-014). |

**Validation rules**
- A company has at most one `Site` (uniqueness on `company`); a second onboard attempt is
  refused (FR-007).
- `maintenance_state` becomes `onboarding` on creation and `active` only after at least one
  kept link exists (FR-011 keeps it at `onboarding` otherwise).
- A company decision of not-approved sets `maintenance_state=suspended`; replay skips
  suspended sites (edge case).

**State transitions**

```text
company approved --> onboarding
onboarding --first kept link survived refilter--> active
active --company rejected--> suspended
suspended --company approved again--> active
```

## Link

A single page address within a site that is a candidate for maintenance, carrying its
discovery state, its refilter verdict, its pipeline stage, its budget state, and its failure
rate (FR-009..FR-015, FR-018, FR-044).

| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | Primary key. |
| site | FK → Site | Owning site. |
| url | URLField (indexed) | Absolute page address (normalized: no fragment, query stripped). |
| url_hash | CharField (indexed) | Normalized hash for de-duplication of discovered links. |
| source | CharField choices | `adaptive_crawl` (default) / `manual` (operator entry for edge cases). |
| review_state | CharField choices | `candidate` / `kept` / `dropped` / `flagged` (FR-010, FR-014). |
| refilter_plan_type | CharField (blank) | Plan type returned by the refilter LLM (FR-013). |
| refilter_confidence | FloatField (null) | Confidence returned by the refilter LLM (FR-013). |
| refilter_flag | BooleanField | True for a borderline keep that needs review (FR-014). |
| pipeline_stage | CharField choices | `discovered` → `refiltered` → `captured` → `extracted` → `classified` → `plans_extracted` → `published`; plus `awaiting_llm_budget`, `flagged`, `dead_lettered` (FR-015, FR-018, FR-048, FR-052). |
| current_trace | FK → Trace (null) | Latest stored trace; null blocks extraction (FR-018). |
| failure_rate | FloatField (default 0) | Derived from domtrack replay failures over the configured window (FR-044). |
| retry_count | PositiveIntegerField (default 0) | Attempts so far for the current stage (FR-052). |
| last_error | CharField (blank) | Last failure reason when the link is flagged or dead-lettered (FR-052). |
| is_active | BooleanField | Participates in scheduled replay. |
| last_replay_at | DateTimeField (null) | Per-link replay recency. |

**Validation rules**
- `(site, url_hash)` is unique so discovery is idempotent; re-discovery does not duplicate a
  link.
- Only `review_state=kept` links are eligible for capture; `dropped` links are excluded and
  preserved as records, never deleted (FR-010, FR-014). `flagged` links are kept and captured
  but routed to review.
- `pipeline_stage` cannot pass `captured` while `current_trace` is null (FR-018).
- A link in `awaiting_llm_budget` has already had its non-LLM stages run; only its LLM-gated
  stage is pending (FR-048).
- A link that exhausts its retry budget becomes `dead_lettered` and is not retried by the
  cycle (FR-052).

**State transitions**

```text
discovered --deterministic policy ok--> refiltered
refiltered --confidently not plans--> dropped     (recorded, never deleted)
refiltered --kept/borderline--> captured          (after headless server capture)
captured --extraction ok--> extracted
captured/extracted --no tables--> flagged         (no tables found, FR-022)
extracted --classified--> classified
classified --plans table extracted--> plans_extracted
plans_extracted --published--> published
any LLM stage --budget exhausted--> awaiting_llm_budget   (FR-048)
awaiting_llm_budget --budget restored--> <resume stage>
any stage --retries exhausted--> dead_lettered            (FR-052)
any --replay failures over threshold--> flagged           (FR-044)
flagged --operator re-runs stages--> discovered           (FR-046)
```

## CaptureSession

The lifecycle of one **server-side headless** capture attempt, so that "recording" is
distinguishable from "stored" and from "failed" (FR-016..FR-019).

| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | Primary key. |
| link | FK → Link | Link being captured. |
| mode | CharField choices | `headless_fixed` (the only mode; headless requires a fixed duration, FR-017). |
| state | CharField choices | `pending` / `recording` / `stored` / `failed` (FR-018). |
| duration_ms | PositiveIntegerField | Fixed recording length (constance default, FR-017). |
| error | CharField (blank) | Set on `failed` (navigation timeout, browser crash, FR-018). |
| trace | FK → Trace (null) | The stored trace once recorded. |

**Validation rules**
- A session leaves `recording` only as `stored` or `failed`; the link does not advance while
  the session is not `stored` (FR-018).
- `failed` sessions are recorded, not deleted, so repeated capture attempts are auditable.
- Only one `pending`/`recording` session per link at a time.
- No operator field: capture is unattended and server-side (FR-016).

## Trace

A domtrack trace file (snapshot plus incremental records) captured for a link, stored as an
artifact in object storage with relational metadata (FR-000a, FR-019).

| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | Primary key. |
| link | FK → Link | Owning link. |
| capture_session | FK → CaptureSession (null) | Session that produced it (null for replay-recorded traces). |
| captured_at | DateTimeField | Capture time (FR-019). |
| origin | CharField choices | `server_capture` / `replay_recording`. |
| storage_key | CharField (unique) | Object key in the artifact store; **UUID-based** (e.g. `traces/<uuid4>.json`). **The file body is never stored in a DB column** (FR-000a). |
| storage_backend | CharField | Alias of the Django `STORAGES` backend used (default `default` = S3-compatible). |
| byte_size | PositiveBigIntegerField | Size of the stored artifact. |
| content_sha256 | CharField (indexed) | Hash for determinism/re-upload detection (SC-010). |
| is_valid_trace | BooleanField | Result of domtrack's trace-validity check at store time (FR-019). |

**Validation rules**
- `storage_key` MUST point at an unmodified domtrack trace file in the configured artifact
  store; no conversion or normalization is applied (FR-000a, SC-009, SC-020).
- `storage_key` is a UUID-based object key, so two captures never collide.
- Artifacts are written and read through Django's `STORAGES` API (`admin_console/artifacts.py`),
  which defaults to S3-compatible storage and is switchable per environment from settings;
  no storage code is written by hand (Principle XII).
- A trace MUST be associated with its link and capture time (FR-019).
- A `Trace` row MUST NOT exist without its stored artifact; the artifact is written before the
  row is committed, and an orphaned object is compensated (FR-053).

## ExtractedTable / ExtractedTableColumn / ExtractedTableRow

The table documents domtrack discovers in a trace, stored as records linked to the link and
trace (FR-020, FR-021). Each page is processed independently; the column `path` is domtrack's
selector and is retained for reference, but nothing downstream binds to it (no recipe).

| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | Primary key. |
| ExtractedTable: trace | FK → Trace | Trace the table was discovered in. |
| ExtractedTable: link | FK → Link | Owning link (denormalized for querying). |
| ExtractedTable: parent | CharField | domtrack's `parent` for the table. |
| ExtractedTable: score | FloatField | domtrack discovery score. |
| ExtractedTable: column_count / row_count | PositiveIntegerField | As reported by domtrack. |
| ExtractedTable: meta | JSONField | domtrack's table `meta` verbatim. |
| Column: table | FK → ExtractedTable | Owning table. |
| Column: column_id | CharField | domtrack's column `id`. |
| Column: label | CharField (blank) | domtrack's `label` (raw until labeling; then the semantic label). |
| Column: path | CharField (indexed) | domtrack's column `path` — retained for diagnostics only. |
| Column: atype | CharField | domtrack's `atype`. |
| Column: slot | CharField (blank) | domtrack's `slot`. |
| Column: coverage | FloatField | domtrack's `coverage`. |
| Column: row_count | PositiveIntegerField | Rows containing this column. |
| Row: table | FK → ExtractedTable | Owning table. |
| Row: row_index | PositiveIntegerField | Position in the table. |
| Row: cells | JSONField | `{column_id: value}` as domtrack reported the row. |

**Validation rules**
- Extraction is deterministic: re-running on the same trace replaces the link/trace's
  existing extraction inside a transaction, yielding identical rows (FR-021, SC-010).
- Zero returned tables sets the link to `flagged` and stores no table rows (FR-022).
- A page's tables are extracted independently; tables are never aligned across pages.

## TableClassification

The LLM verdict marking an extracted table as a plans table or not, with its plan type and
confidence (FR-023..FR-025). It is the anchor replay uses to decide whether a detected change
is relevant, and it is the reference published records carry as provenance.

| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | Primary key. |
| table | OneToOneField → ExtractedTable | Classified table (one verdict per table). |
| is_plans_table | BooleanField | The verdict (FR-023). |
| plan_type | CharField (blank) | Matched plan type from the code schema, when a plans table (FR-023). |
| confidence | FloatField | The model's confidence in the verdict (FR-023). |
| provider / model | CharField | LLM provider and model used (from configuration). |
| prompt_version | CharField | Prompt template version, for reproducibility. |
| classified_at | DateTimeField | Inherited. |

**Validation rules**
- Exactly one classification row per extracted table; a re-classification replaces it in a
  transaction.
- Classification is per table and per page: a page may hold zero, one, or several
  `is_plans_table=true` verdicts (FR-024).
- Classification is LLM-gated: when the token budget is exhausted, no row is written and the
  table's link waits in `awaiting_llm_budget` (FR-048).

## PlanRecord

A normalized plan extracted from a plans table by the LLM against the code plan schema
(FR-026..FR-031). It contains **data only** — no selectors and no formulas.

| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | Primary key. |
| link | FK → Link | Owning link. |
| table | FK → ExtractedTable | Plans table it was extracted from. |
| classification | FK → TableClassification | The plans-table verdict that made it eligible (provenance, FR-037). |
| plan_type | CharField | Plan type key from the code schema (FR-027). |
| natural_key | CharField (indexed) | Stable key for upserts across replays (e.g. plan name + link). |
| values | JSONField | Normalized field values keyed by schema field key (FR-028). |
| confidence | FloatField (null) | Optional model confidence for the extraction. |
| prompt_version | CharField | Prompt template version, for reproducibility. |
| extracted_at | DateTimeField | Inherited. |

**Validation rules**
- `values` MUST be shaped by the schema for `plan_type`; a record with an unpopulated
  required field is not produced — that table is skipped (FR-030). Required-field member
  ship is checked in `admin_console` and re-checked (shape) at the `catalog` boundary.
- Extraction is idempotent for an unchanged table: re-running yields the same records
  (FR-031).
- No selector, formula, or recipe is persisted anywhere in the extraction path (FR-028,
  SC-012).
- Re-extraction is LLM-gated: when the token budget is exhausted, the link waits in
  `awaiting_llm_budget` (FR-048).

## SemanticLabel

The optional, admin-enabled LLM-produced table purpose and column labels (FR-032..FR-035).
Absent entirely when labeling is disabled or budget-blocked.

| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | Primary key. |
| table | FK → ExtractedTable | Labeled table. |
| column_id | CharField (blank) | Empty for a table-level label; set for a column label. |
| label | CharField | Meaningful name/purpose produced by domtrack's labeling. |
| provider / model | CharField | Provider and model used (from constance). |
| language | CharField | Label language (from constance; default `fa`). |
| created_at | DateTimeField | Inherited. |

**Validation rules**
- Rows exist only when the admin toggle was on and the call was permitted by the token
  budget (FR-032, FR-035).
- Labels never gate another stage: extraction, classification, plan extraction, publishing,
  and replay behave identically with or without label rows (FR-034, SC-019).

## PlanSchema (code, not a table)

The single, code-defined schema representing a host or server plan, with a plan-type
dimension (FR-027). Defined in `admin_console/plan_schema.py` as Pydantic models; never
user-editable (edited by hand in code). It is the target the LLM extraction fills.

```text
PlanSchema
├── plan_type: "hosting"
│   ├── field: plan_name        text   required
│   ├── field: storage_amount   number required  unit_family: data_size
│   ├── field: storage_unit     enum   required  values: [GB, TB]
│   ├── field: ram_amount       number required  unit_family: data_size
│   ├── field: cpu_cores        number required
│   ├── field: bandwidth_amount number required  unit_family: data_size
│   ├── field: price_amount     number required  unit_family: currency
│   └── field: billing_period   enum   required  values: [monthly, yearly]
├── plan_type: "cdn"
│   ├── field: plan_name        text   required
│   ├── field: traffic_amount   number required  unit_family: data_size
│   ├── field: request_rate     number optional  unit_family: rate
│   └── field: price_amount     number required  unit_family: currency
└── plan_type: "virtual_server"
    ├── field: plan_name        text   required
    ├── field: vcpu_cores       number required
    ├── field: ram_amount       number required  unit_family: data_size
    ├── field: disk_amount      number required  unit_family: data_size
    ├── field: os               enum   optional
    └── field: price_amount     number required  unit_family: currency
```

**Validation rules**
- Field `key` is the stable identity plan records are keyed by; removing a field is a
  breaking change handled by a documented migration of existing plan records.
- `required=true` fields gate whether a table can be extracted; a table whose extraction
  cannot fill a required field is skipped (FR-030).
- `unit_family` documents the units the LLM normalizes to in `PlanRecord.values` (FR-028);
  there is no formula-cleaning engine.
- The `enum` `values` constrain the normalized values the LLM emits.

## PublishedRecord

**Owned by `catalog`** (not `admin_console`): this is the published plan data that catalog
and search consume, so its model and migration live in the `catalog` app. `admin_console`
writes it only through `catalog/interfaces.py` (`catalog.services.upsert_published_record` /
`retire_published_record`), passing opaque `site`/`link`/`trace`/`classification` ids so
`catalog` never imports `admin_console` internals (Principle V). A published plan record with
provenance to its site, link, trace, and the plans-table classification (FR-036..FR-038).

| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | Primary key. |
| site / link / trace / classification | Integer id (indexed) | Opaque references for provenance (FR-037); no cross-app FK constraint, so `catalog` stays independent of `admin_console`. |
| source | CharField | Which pipeline produced it (`admin_console`), for future producers. |
| plan_type | CharField | Which plan type the record belongs to (FR-027). |
| natural_key | CharField (indexed) | Stable key used for upserts across replays (e.g. plan name + link). |
| values | JSONField | Normalized field values keyed by `schema_field_key` (FR-028). |
| is_published | BooleanField | Set false when a replay reports the item removed (FR-038). |
| published_at / retired_at | DateTimeField (null) | Publication and retirement times. |

**Validation rules**
- Nothing is published while a required field of the plan is unpopulated — FR-030. The check
  lives in `admin_console` (it owns the schema extraction); `catalog` accepts only a payload
  `admin_console` has already validated, and it validates the payload shape (Pydantic) at the
  interface boundary.
- Records are upserted by `(source, site, natural_key)` so a replay updates rather than
  duplicates.
- A removed item is retired (`is_published=false`, `retired_at` set), never left stale
  (FR-038).
- `catalog` never imports `admin_console`: it receives ids and payloads, never
  `admin_console` model objects (Principle V).

## ReplayRun / ChangeRecord

A scheduled domtrack **compare** run (replay, record, diff in one call) of a link that yields
changes classified as content or structural, plus data updates and a failure count
(FR-039..FR-043).

| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | Primary key. |
| ReplayRun: link | FK → Link | Replayed link. |
| ReplayRun: scheduled_for / started_at / finished_at | DateTimeField | Cycle timing; `scheduled_for` drives due-run selection (FR-039). |
| ReplayRun: state | CharField choices | `scheduled` / `running` / `succeeded` / `failed` / `awaiting_llm_budget`. |
| ReplayRun: before_trace | FK → Trace | The trace replayed. |
| ReplayRun: after_trace | FK → Trace (null) | The fresh recording produced during replay. |
| ReplayRun: diff_summary | JSONField | domtrack diff summary: `a_nodes,b_nodes,added,removed,changed`. |
| ReplayRun: reextracted | BooleanField | Whether the run triggered LLM re-extraction (FR-042). |
| ReplayRun: stats_applied / stats_skipped / stats_failed | PositiveIntegerField | domtrack replay stats (failure rate derives from these, FR-044). |
| ReplayRun: failures | JSONField | domtrack's failure entries (selector, reason) for operator diagnostics. |
| ChangeRecord: replay_run | FK → ReplayRun | Owning run. |
| ChangeRecord: change_kind | CharField choices | `content` / `structural` (FR-041). |
| ChangeRecord: touches_plans_table | BooleanField | Whether the change touches a region classified as a plans table (FR-042). |
| ChangeRecord: classification | FK → TableClassification (null) | The plans-table verdict the change matched, when applicable. |
| ChangeRecord: summary | JSONField | Bounded description of the change (added/removed/changed counts and selectors). |

**Validation rules**
- The next run for a link is due when `now - link.last_replay_at >= REPLAY_PERIOD_HOURS`
  (constance, FR-039, FR-054).
- Only links with an active site and at least one plans-table classification are replayed
  (FR-042, FR-039).
- A change is re-extracted only when `touches_plans_table=true`; when the change is
  `structural`, the run re-discovers tables and re-classifies before re-extraction (FR-042).
- Changes that do not touch a plans table produce no LLM work (FR-043, SC-015).
- `stats_failed` over the trailing `FAILURE_RATE_WINDOW_RUNS` recomputes `Link.failure_rate`
  (FR-044).
- When the token budget is exhausted, the run parks in `awaiting_llm_budget` and resumes
  (FR-048).

## FailureAlert (admin_console)

The link-state alert raised when a link's failure rate crosses the threshold (FR-044).
This model records **what is wrong** (which link needs updating and how severe it is);
**how it is delivered** is owned by the `notifications` app (below). State-based so it is
raised once per crossing, not once per replay.

| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | Primary key. |
| link | FK → Link | Link that needs updating. |
| state | CharField choices | `open` / `resolved`. |
| failure_rate | FloatField | Rate at the time of raising. |
| raised_at / resolved_at | DateTimeField | Crossing window; a fall back below the threshold resolves it, and a later rise re-opens a new alert. |
| notification_dedup_key | CharField (indexed) | Key passed to the `notifications` app so one crossing raises exactly one notification per recipient (FR-045, edge case). |

**Validation rules**
- One `open` alert per link at a time; a repeat crossing after resolution creates a new
  alert (edge case: alert is not repeated every subsequent replay).
- Every open alert raises one notification through the `notifications` app, which fans it out
  to every active recipient over the in-app channel (email is out of scope by project
  decision) (FR-045).

## Notification / NotificationRecipient / NotificationDelivery (notifications app)

General-purpose notification models owned by the new **`notifications` app**, not by
`admin_console`. Failure alerts are one `event_type` among others (approval notices, budget
exhaustion, provider degradation). Callers publish through `notifications/interfaces.py`;
they never write these tables directly (Principle V).

| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | Primary key. |
| Notification: event_type | CharField (indexed) | Typed event, e.g. `link_failure_rate_exceeded`, `llm_budget_exhausted`. |
| Notification: severity | CharField choices | `info` / `warning` / `critical`. |
| Notification: subject / body | CharField / TextField | Human-readable content (personal data masked, SC-021). |
| Notification: related_object | CharField | Opaque reference to the source object (e.g. `admin_console.Link:901`), so the app stays producer-agnostic. |
| Notification: dedup_key | CharField (blank, indexed) | Idempotency key; a repeated publish with the same key does not duplicate a notification. |
| Notification: created_at | DateTimeField | Inherited. |
| Delivery: notification | FK → Notification | Owning notification. |
| Delivery: recipient | FK → NotificationRecipient | Recipient. |
| Delivery: channel | CharField choices | `in_app` (pluggable; more channels can be added without changing callers, but email is not implemented by decision). |
| Delivery: state | CharField choices | `pending` / `sent` / `failed`. |
| Delivery: sent_at / read_at | DateTimeField (null) | Delivery and read markers; `read_at` applies to the in-app channel. |
| Delivery: error | CharField (blank) | Non-blocking delivery failure detail. |
| Recipient: user | FK → `accounts.User` | The platform user who receives in-app notifications. |
| Recipient: name | CharField (blank) | Optional display name. |
| Recipient: is_active | BooleanField | Removed recipients are deactivated, preserving notification history. |
| Recipient: created_by | FK → `accounts.User` (null) | Admin who added it. |

**Validation rules**
- Only admins can add, deactivate, or list recipients (FR-045).
- Deactivating a recipient never rewrites previously delivered notifications.
- Each notification produces one `NotificationDelivery` row per active recipient on the
  `in_app` channel (FR-045).
- Delivery runs from a `django.tasks` task, so the producer (the replay run) is never blocked
  by delivery; a failed delivery is recorded and does not block the others.
- `dedup_key` prevents duplicate notifications when the same alert state is re-evaluated.

## LlmCostLedger / LLM token budget

The model-backed **LLM token budget** and its spend record (Principle II, FR-047..FR-050).
Every LLM-gated stage — refilter, classification, schema extraction, labeling — consults this
budget before calling the model, and appends a spend row after.

| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | Primary key. |
| scope | CharField choices | `global` / per-provider/model key. |
| token_budget | BigIntegerField (null) | Configurable token budget; null means "no budget set". |
| period | CharField choices | `daily` / `monthly` / `total`. |
| updated_by | FK → `accounts.User` (null) | Admin who last changed the budget. |
| timestamp | DateTimeField | For spend rows: when the LLM call happened. |
| tokens_used | BigIntegerField | For spend rows: tokens consumed by one LLM call. |
| amount | DecimalField (null) | For spend rows: cost of the call, when the provider reports it. |
| stage | CharField choices | `refilter` / `classification` / `schema_extraction` / `labeling` (FR-047). |
| link_ref | FK → Link (null) | Link whose call incurred the spend (attribution, FR-049). |
| table_ref | FK → ExtractedTable (null) | Table whose call incurred the spend, when applicable (FR-049). |
| idempotency_key | CharField (unique) | Guards one logical LLM call so a retry is not charged twice (FR-050). |

**Validation rules**
- The budget is read (never hard-coded) before each LLM-gated call; when the pending call
  would exceed `token_budget` for the period, the call is not made, no classification/plan
  row is written, the link enters `awaiting_llm_budget`, and the admin is notified
  (FR-048, FR-049).
- Non-LLM stages do not consult the budget and continue regardless (FR-048, SC-016).
- Every LLM call appends exactly one spend row keyed by `idempotency_key`; a retried call
  reuses its key and does not append a second row (FR-050).
- Budget exhaustion raises an admin alert; a silent exhaustion is forbidden.

## Cross-Entity Invariants

- **One site per company** (FR-007): `Site.company` is unique.
- **No advance without a trace** (FR-018): `Link.pipeline_stage` cannot pass `captured`
  while `Link.current_trace` is null.
- **No plans/no publish** (FR-030): `admin_console` writes a `catalog.PublishedRecord` only
  for a plan record extracted from a table with `is_plans_table=true` and a populated
  required field set.
- **No recipes** (FR-028): no table stores a selector, formula, or extraction recipe; the
  plan schema (code) and the LLM extraction are the only contract.
- **domtrack traces are opaque** (FR-000a): no table stores trace content or a converted
  form of it; traces live in the `STORAGES`-configured artifact store under UUID keys, and a
  stored object never exists without its `Trace` row (FR-053).
- **Provenance is complete** (FR-037): every `catalog.PublishedRecord` carries site, link,
  trace, and classification references.
- **No LLM beyond budget** (FR-048): every LLM-gated stage is preceded by a budget check, and
  exhausted work parks in `awaiting_llm_budget` rather than blocking non-LLM stages.
- **Idempotent spend** (FR-050): `LlmCostLedger.idempotency_key` is unique.
- **Interface-only boundaries** (Principle V): `admin_console` writes published records only
  through `catalog/interfaces.py` and raises notifications only through
  `notifications/interfaces.py`; neither app imports `admin_console`.
- **Append-only decisions** (FR-002, FR-006): `companies.VerificationDecision` rows are
  insert-only; `admin_console` never updates or deletes one.
- **No personal data in logs** (SC-021): events carry ids and hashes, never phone numbers or
  trace content.
