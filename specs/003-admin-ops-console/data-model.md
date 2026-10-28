# Data Model: Admin Console — Company Approval & Site Data Maintenance

Entities extracted from [spec.md](./spec.md) Key Entities and Functional Requirements.
All persistent domain models inherit `utils.models.TimestampedModel` (audit timestamps).
Field types are indicative; exact column types follow Django conventions. Ownership by app:

- `admin_console` (new): Site, Link, CaptureSession, Trace metadata, extracted tables,
  SemanticLabel, ExtractionRecipe / RecipeFieldBinding, ReplayRun, and LlmCostLedger.
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
| Link | `admin_console` | FR-009..FR-011, FR-014, FR-030 |
| CaptureSession | `admin_console` | FR-012..FR-017 |
| Trace | `admin_console` | FR-016, FR-018, FR-000a |
| ExtractedTable / Column / Row | `admin_console` | FR-018..FR-020 |
| SemanticLabel | `admin_console` | FR-021..FR-024 |
| ExtractionRecipe / RecipeFieldBinding | `admin_console` | FR-025..FR-031 |
| PlanSchema (code) | `admin_console` (code) | FR-027 |
| PublishedRecord | `catalog` | FR-034..FR-036 |
| ReplayRun | `admin_console` | FR-037..FR-040 |
| FailureAlert | `admin_console` | FR-040 |
| Notification / NotificationRecipient / NotificationDelivery | `notifications` | FR-041 |
| LlmCostLedger | `admin_console` | FR-024 (Principle II) |

## Site

The single crawl target for an approved company, identified by the company's registered
domain (FR-007). Created when a company is approved and its maintenance lifecycle starts.

| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | Primary key. |
| company | OneToOneField → `companies.Company` | **One site per company** (FR-007); uniqueness enforced at the DB. Referenced through the interface, not joined on in other modules. |
| domain | CharField (indexed) | Normalized company domain, copied from the company at onboarding. |
| has_sitemap | BooleanField | Whether a discoverable sitemap was found (FR-008). |
| sitemap_url | URLField (blank) | The sitemap actually used, when discovered. |
| maintenance_state | CharField choices | `onboarding` / `active` / `suspended` (FR-003, FR-011, edge case: rejection suspends). |
| onboarded_at | DateTimeField (null) | When onboarding completed. |
| last_replay_at | DateTimeField (null) | Set on each replay cycle; drives staleness (FR-037, SC-012). |

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
onboarding --first kept link kept--> active
active --company rejected--> suspended
suspended --company approved again--> active
```

## Link

A single page address within a site that is a candidate for capture, carrying its review
state, pipeline stage, and failure rate (FR-009..FR-011, FR-030, FR-040).

| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | Primary key. |
| site | FK → Site | Owning site. |
| url | URLField (indexed) | Absolute page address. |
| url_hash | CharField (indexed) | Normalized hash for de-duplication of discovered links. |
| source | CharField choices | `sitemap` / `manual` (FR-008). |
| review_state | CharField choices | `candidate` / `kept` / `removed` (FR-009, FR-010). |
| pipeline_stage | CharField choices | `review` → `capture` → `extracted` → `mapped` → `cleaned` → `published`; plus `flagged` and `failed` (FR-014, FR-020, FR-030). |
| current_trace | FK → Trace (null) | Latest stored trace; null blocks extraction (FR-014). |
| failure_rate | FloatField (default 0) | Derived from domtrack replay failures over the configured window (FR-040). |
| is_active | BooleanField | Participates in scheduled replay. |
| last_replay_at | DateTimeField (null) | Per-link replay recency. |

**Validation rules**
- `(site, url_hash)` is unique so discovery is idempotent; re-discovery does not duplicate a
  link.
- Only `review_state=kept` links are eligible for capture; `removed` links are excluded and
  preserved as records, never deleted (FR-010).
- `pipeline_stage` cannot pass `capture` while `current_trace` is null (FR-014).
- A link cannot reach `mapped` (or be published) while any required schema field lacks a
  binding for its recipe (FR-030).

**State transitions**

```text
candidate --keep--> kept
candidate/kept --remove--> removed          (recorded, never deleted)
kept --trace stored--> capture
capture --extraction ok--> extracted
capture/extracted --no tables--> flagged    (operator may re-capture, FR-020)
extracted --recipe complete--> mapped
mapped --cleaning done--> cleaned
cleaned --published--> published
any --replay failures over threshold--> flagged   (FR-040)
flagged --operator re-runs stages--> capture       (FR-042, SC-014)
```

## CaptureSession

The lifecycle of one operator-driven capture attempt, so that "recorded but not yet
stored" is distinguishable from "cancelled" and from "stored" (FR-012..FR-017).

| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | Primary key. |
| link | FK → Link | Link being captured. |
| operator | FK → `accounts.User` | Operator who triggered it (FR-016). |
| mode | CharField choices | `interactive` (default, non-headless) / `fixed_duration` (FR-013). |
| state | CharField choices | `pending` / `recording` / `awaiting_upload` / `stored` / `failed` (FR-014, FR-015, FR-017). |
| local_path | CharField (blank) | Trace path reported by the operator's local domtrack. |
| duration_ms | PositiveIntegerField (null) | Set for `fixed_duration` captures. |
| error | CharField (blank) | Set on `failed` (e.g. domtrack unreachable, FR-017). |
| trace | FK → Trace (null) | The stored trace once uploaded. |

**Validation rules**
- A session leaves `recording` only as `awaiting_upload` (domtrack reported a path),
  `failed`, or `stored`; the link does not advance while the session is not `stored`
  (FR-014).
- `failed` sessions are recorded, not deleted, so repeated capture attempts are auditable.
- Only one `pending`/`recording`/`awaiting_upload` session per link at a time.

## Trace

A domtrack trace file (snapshot plus incremental records) captured for a link, stored as an
artifact in object storage with relational metadata (FR-000a, FR-016).

| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | Primary key. |
| link | FK → Link | Owning link. |
| capture_session | FK → CaptureSession (null) | Session that produced it (null for replay-recorded traces). |
| captured_by | FK → `accounts.User` (null) | Operator; null for server-side replay recordings (FR-016). |
| captured_at | DateTimeField | Capture time (FR-016). |
| origin | CharField choices | `operator_capture` / `replay_recording`. |
| storage_key | CharField (unique) | Object key in the artifact store; **UUID-based** (e.g. `traces/<uuid4>.json`) so the name is unique and independent of the operator's local path. **The file body is never stored in a DB column** (FR-000a). |
| storage_backend | CharField | Alias of the Django `STORAGES` backend used (default `default` = S3-compatible). Lets the same row describe an artifact written to S3 or, in dev, local filesystem. |
| byte_size | PositiveBigIntegerField | Size of the stored artifact. |
| content_sha256 | CharField (indexed) | Hash for determinism/re-upload detection (SC-008). |
| is_valid_trace | BooleanField | Result of domtrack's trace-validity check at store time (FR-016). |

**Validation rules**
- `storage_key` MUST point at an unmodified domtrack trace file in the configured artifact
  store; no conversion or normalization is applied (FR-000a, SC-007, SC-017).
- `storage_key` is a UUID-based object key, so two captures never collide and the stored name
  never reveals the operator's filesystem path; the `Trace` row is the only mapping back to
  the link.
- Artifacts are written and read through Django's `STORAGES` API (`admin_console/artifacts.py`),
  which defaults to S3-compatible storage and is switchable per environment from settings;
  no storage code is written by hand (Principle XII).
- A trace MUST be associated with its link and, when operator-captured, its operator and
  capture time (FR-016).

## ExtractedTable / ExtractedTableColumn / ExtractedTableRow

The table documents domtrack discovers in a trace, stored as records linked to the link and
trace (FR-018, FR-019). Column `path` is domtrack's selector and is the source selector the
recipe later binds (FR-028).

| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | Primary key. |
| ExtractedTable: trace | FK → Trace | Trace the table was discovered in. |
| ExtractedTable: link | FK → Link | Owning link (denormalized for querying). |
| ExtractedTable: parent | CharField | domtrack's `parent` for the table. |
| ExtractedTable: score | FloatField | domtrack discovery score (why this candidate was chosen). |
| ExtractedTable: column_count / row_count | PositiveIntegerField | As reported by domtrack. |
| ExtractedTable: meta | JSONField | domtrack's table `meta` verbatim. |
| Column: table | FK → ExtractedTable | Owning table. |
| Column: column_id | CharField | domtrack's column `id`. |
| Column: label | CharField (blank) | domtrack's `label` (raw until labeling; then the semantic label). |
| Column: path | CharField (indexed) | domtrack's column `path` — **the source selector** (FR-028). |
| Column: atype | CharField | domtrack's `atype`. |
| Column: slot | CharField (blank) | domtrack's `slot`. |
| Column: coverage | FloatField | domtrack's `coverage`. |
| Column: row_count | PositiveIntegerField | Rows containing this column. |
| Row: table | FK → ExtractedTable | Owning table. |
| Row: row_index | PositiveIntegerField | Position in the table. |
| Row: cells | JSONField | `{column_id: value}` as domtrack reported the row. |

**Validation rules**
- Extraction is deterministic: re-running on the same trace replaces the link/trace's
  existing extraction inside a transaction, yielding identical rows (FR-019, SC-008).
- Zero returned tables sets the link to `flagged` and stores no table rows (FR-020).
- Every column keeps domtrack's `path` unchanged; the recipe references it as an immutable
  string.

## SemanticLabel

The optional, admin-enabled LLM-produced table purpose and column labels (FR-021..FR-024).
Absent entirely when labeling is disabled or ceiling-blocked (FR-023).

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
- Rows exist only when the admin toggle was on and the LLM call was permitted by the
  ceiling (FR-021, FR-024).
- Labels never gate another stage: extraction, mapping, cleaning, publishing, and replay
  behave identically with or without label rows (FR-023, SC-016).
- The semantic label is stored separately from the column's raw domtrack `label` so the raw
  value is never lost.

## ExtractionRecipe / RecipeFieldBinding

The durable artifact of mapping (FR-028): per schema field, the source selector and the
combination formula. Versioned so a re-map keeps history while published provenance keeps
pointing at the version that produced it (FR-035).

| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | Primary key. |
| Recipe: link | FK → Link | Owning link. |
| Recipe: plan_type | CharField | Plan-type key from the code schema (FR-027). |
| Recipe: version | PositiveIntegerField | Incremented on each save. |
| Recipe: is_current | BooleanField | Exactly one current version per link. |
| Recipe: is_complete | BooleanField | True only when every required field for `plan_type` is bound (FR-030). |
| Binding: recipe | FK → ExtractionRecipe | Owning recipe. |
| Binding: schema_field_key | CharField | Field key in the code plan schema (FR-027). |
| Binding: source_table | FK → ExtractedTable | Table the value comes from (supports cross-table merge, FR-026). |
| Binding: source_column | FK → ExtractedTableColumn | Column whose `path` is the selector (FR-028). |
| Binding: selector | CharField | Snapshot of the column `path` at save time. |
| Binding: formula | CharField | The combination formula over source values, written in an **Excel/spreadsheet-compatible** syntax (cell/column references, spreadsheet operators and functions such as `SUM`, `IF`, `ROUND`, `&`; `,` argument separator) so it is valid to paste into Excel/LibreOffice/Sheets (FR-028). |
| Binding: aggregation | CharField (blank) | Optional per-row aggregation (`row`, `sum`, `min`, `max`, `concat`) when the field spans rows. |

**Validation rules**
- `formula` is validated against a whitelisted, **Excel/spreadsheet-compatible** function and
  operator set over column references; an invalid or non-spreadsheet-valid formula is
  rejected at the boundary with the offending field named (no `eval`, no arbitrary code).
- `is_complete` is computed by comparing bound `schema_field_key`s against the required set
  for `plan_type`; a link cannot become `mapped` while it is false (FR-030, SC-009).
- Exactly one recipe per link has `is_current=true`.
- Reopening the workspace returns the current recipe's bindings, selectors, and formulas
  (FR-031).
- Every subsequent replay evaluates the current recipe; no operator re-mapping is required
  (FR-029, SC-010).

## PlanSchema (code, not a table)

The single, code-defined schema representing a host or server plan, with a plan-type
dimension (FR-027). Defined in `admin_console/plan_schema.py`; never user-editable.

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
- Field `key` is the stable identity recipes bind to; removing a field is a breaking
  change handled by a documented migration of existing bindings.
- `required=true` fields participate in the recipe-completeness gate (FR-030).
- `unit_family` feeds the cleaning engine's standardization rules (FR-032).
- The `enum` `values` constrain cleaning's category normalization.

## PublishedRecord

**Owned by `catalog`** (not `admin_console`): this is the published plan data that catalog
and search consume, so its model and migration live in the `catalog` app. `admin_console`
writes it only through `catalog/interfaces.py` (`catalog.services.upsert_published_record` /
`retire_published_record`), passing opaque `site`/`link`/`trace`/`recipe` ids so `catalog`
never imports `admin_console` internals (Principle V). A cleaned, filterable unit of data
placed on the main site, with provenance to its site, link, trace, and recipe
(FR-034..FR-036).

| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | Primary key. |
| site / link / trace / recipe | Integer id (indexed) | Opaque references for provenance (FR-035); no cross-app FK constraint, so `catalog` stays independent of `admin_console`. |
| source | CharField | Which pipeline produced it (`admin_console`), for future producers. |
| plan_type | CharField | Which plan type the record belongs to (FR-027). |
| natural_key | CharField (indexed) | Stable key used for upserts across replays (e.g. plan name + link). |
| values | JSONField | Cleaned, standardized field values keyed by `schema_field_key`. |
| cleaning_exceptions | JSONField | Fields cleaning could not standardize (empty when fully clean). |
| is_published | BooleanField | Set false when a replay reports the item removed (FR-036). |
| published_at / retired_at | DateTimeField (null) | Publication and retirement times. |

**Validation rules**
- Nothing is published while a required field is unconnected (no `is_complete` recipe) —
  FR-030, SC-009. The check itself lives in `admin_console` (it owns the recipe); `catalog`
  accepts only a payload `admin_console` has already validated, and it validates the payload
  shape (Pydantic) at the interface boundary.
- Records are upserted by `(source, site, natural_key)` so a replay updates rather than
  duplicates.
- A removed item is retired (`is_published=false`, `retired_at` set), never left stale
  (FR-036).
- A record with cleaning exceptions keeps its cleaned fields and remains publishable, with
  the exceptions surfaced to the operator (FR-033).
- `catalog` never imports `admin_console`: it receives ids and payloads, never
  `admin_console` model objects (Principle V).

## ReplayRun

A scheduled domtrack replay of a link that records the current page, diffs it against the
previous trace via domtrack's compare capability, and yields data updates plus a failure
count (FR-037..FR-039).

| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | Primary key. |
| link | FK → Link | Replayed link. |
| recipe | FK → ExtractionRecipe | Recipe version used (provenance for the update). |
| scheduled_for / started_at / finished_at | DateTimeField | Cycle timing; `scheduled_for` drives due-run selection (FR-037). |
| state | CharField choices | `scheduled` / `running` / `succeeded` / `failed`. |
| before_trace | FK → Trace | The trace replayed. |
| after_trace | FK → Trace (null) | The fresh recording produced during replay (record-during-replay). |
| diff_summary | JSONField | domtrack diff summary: `a_nodes,b_nodes,added,removed,changed`. |
| diff_applied | BooleanField | Whether the diff was applied to published data (FR-039). |
| stats_applied / stats_skipped / stats_failed | PositiveIntegerField | domtrack replay stats (failure rate derives from these, FR-040). |
| failures | JSONField | domtrack's failure entries (selector, reason) for operator diagnostics. |

**Validation rules**
- The next run for a link is due when `now - link.last_replay_at >= REPLAY_PERIOD_HOURS`
  (constance, FR-037, FR-043).
- Only links with an active site and a complete recipe are replayed (FR-029, FR-037).
- `stats_failed` over the trailing `FAILURE_RATE_WINDOW_RUNS` recomputes `Link.failure_rate`
  (FR-040).

## FailureAlert (admin_console)

The link-state alert raised when a link's failure rate crosses the threshold (FR-040).
This model records **what is wrong** (which link needs updating and how severe it is);
**how it is delivered** is owned by the `notifications` app (below). State-based so it is
raised once per crossing, not once per replay; the actual message is dispatched through
`notifications/interfaces.py`.

| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | Primary key. |
| link | FK → Link | Link that needs updating. |
| state | CharField choices | `open` / `resolved`. |
| failure_rate | FloatField | Rate at the time of raising. |
| raised_at / resolved_at | DateTimeField | Crossing window; a fall back below the threshold resolves it, and a later rise re-opens a new alert. |
| notification_dedup_key | CharField (indexed) | Key passed to the `notifications` app so one crossing raises exactly one notification per recipient (FR-041, edge case). |

**Validation rules**
- One `open` alert per link at a time; a repeat crossing after resolution creates a new
  alert (edge case: alert is not repeated every subsequent replay).
- Every open alert raises one notification through the `notifications` app, which fans it out
  to every active recipient over the in-app channel (email is out of scope by project
  decision) (FR-041).

## Notification / NotificationRecipient / NotificationDelivery (notifications app)

General-purpose notification models owned by the new **`notifications` app**, not by
`admin_console`. Failure alerts are one `event_type` among others (approval notices,
provider degradation, LLM ceiling breaches). Callers publish through
`notifications/interfaces.py`; they never write these tables directly (Principle V).

| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | Primary key. |
| Notification: event_type | CharField (indexed) | Typed event, e.g. `link_failure_rate_exceeded`, `llm_ceiling_exceeded`. |
| Notification: severity | CharField choices | `info` / `warning` / `critical`. |
| Notification: subject / body | CharField / TextField | Human-readable content (personal data masked, SC-018). |
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
- Only admins can add, deactivate, or list recipients (FR-041).
- Deactivating a recipient never rewrites previously delivered notifications.
- Each notification produces one `NotificationDelivery` row per active recipient on the
  `in_app` channel (FR-041).
- Delivery runs from a `django.tasks` task, so the producer (the replay run) is never blocked
  by delivery; a failed delivery is recorded and does not block the others.
- `dedup_key` prevents duplicate notifications when the same alert state is re-evaluated.

## LlmCostLedger

The model-backed LLM cost ceiling and its spend record (Principle II, FR-024).

| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | Primary key. |
| scope | CharField choices | `global` / per-provider/model key. |
| ceiling_amount | DecimalField (null) | Configurable ceiling; null means "ceiling not set". |
| period | CharField choices | `daily` / `monthly` / `total`. |
| updated_by | FK → `accounts.User` (null) | Admin who last changed the ceiling. |
| timestamp | DateTimeField | For spend rows: when the labeled call happened. |
| amount | DecimalField | For spend rows: the cost of one labeling call. |
| label_run_ref | FK → Link (null) | Link whose labeling incurred the cost. |

**Validation rules**
- The ceiling is read (never hard-coded) before each domtrack labeling call; when the
  pending call would exceed `ceiling_amount` for the period, labeling stops, no
  `SemanticLabel` rows are written, and the situation is reported and recorded (FR-024).
- Every labeling call appends a spend row; the period total is the projection of those rows,
  so breaches are observable and auditable (Principle II).
- Breaching the ceiling also raises an admin alert; a silent breach is forbidden.

## Cross-Entity Invariants

- **One site per company** (FR-007): `Site.company` is unique.
- **No advance without a trace** (FR-014): `Link.pipeline_stage` cannot pass `capture`
  while `Link.current_trace` is null.
- **No unmapped publish** (FR-030): `admin_console` writes a `catalog.PublishedRecord` only
  for a link whose current recipe `is_complete=true`.
- **domtrack traces are opaque** (FR-000a): no table stores trace content or a converted
  form of it; traces live in the `STORAGES`-configured artifact store under UUID keys.
- **Provenance is complete** (FR-035): every `catalog.PublishedRecord` carries site, link,
  trace, and recipe references.
- **Interface-only boundaries** (Principle V): `admin_console` writes published records only
  through `catalog/interfaces.py` and raises notifications only through
  `notifications/interfaces.py`; neither app imports `admin_console`.
- **Append-only decisions** (FR-002, FR-006): `companies.VerificationDecision` rows are
  insert-only; `admin_console` never updates or deletes one.
- **No personal data in logs** (SC-018): events carry ids and hashes, never phone numbers or
  trace content.
