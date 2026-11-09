# pipeline — Data Model

All models inherit `TimestampedModel` (soft delete). Table names are prefixed
`admin_console_*` for historical reasons.

## Site

Table: `admin_console_site`

| Column | Notes |
|---|---|
| `company_id` | one-to-one → `companies_company` |
| `domain` | crawl seed |
| `maintenance_state` | `onboarding` / `active` / `suspended` |
| `onboarded_at`, `last_discovered_at`, `last_replay_at` | timestamps |

## Link

Table: `admin_console_link`

| Column | Notes |
|---|---|
| `site_id` | FK |
| `url`, `url_hash` | unique per site among active rows |
| `source` | `adaptive_crawl` / `manual` |
| `review_state` | `candidate` / `kept` / `dropped` / `flagged` |
| `pipeline_stage` | see stage machine |
| `current_trace_id` | FK → `Trace` |
| `failure_rate` | trailing failure ratio |
| `retry_count`, `last_error` | resilience state |
| `pipeline_task_state` | `idle` / `queued` / `running` / `completed` / `failed` |
| `is_active`, `last_replay_at` | |

Constraint: unique `(site, url_hash)` where `deleted_at IS NULL`.

## CaptureSession

Table: `admin_console_capture_session`

| Column | Notes |
|---|---|
| `link_id` | FK |
| `mode` | `headless_fixed` |
| `state` | `pending` / `recording` / `stored` / `failed` |
| `duration_ms`, `error`, `trace_id` | |

Constraint: at most one non-terminal session per link.

## Trace

Table: `admin_console_trace`

| Column | Notes |
|---|---|
| `link_id` | FK |
| `capture_session_id` | nullable |
| `captured_at`, `origin` | `server_capture` / `replay_recording` |
| `storage_key`, `storage_backend` | artifact location |
| `content_sha256` | integrity/dedupe |
| `is_valid_trace` | |

The trace body is never stored in the database.

## ExtractedTable / Column / Row

- `admin_console_extracted_table`: `trace`, `link`, `table_index`, `parent`, `score`,
  `column_count`, `row_count`, `meta`.
- `admin_console_extracted_column`: `column_id`, `label`, `path`, `atype`, `slot`,
  `coverage`, `row_count`.
- `admin_console_extracted_row`: `row_index`, `cells` (column_id → value).

Unique row index per table.

## TableClassification

Table: `admin_console_table_classification`

| Column | Notes |
|---|---|
| `table_id` | one-to-one |
| `is_price_table` | rule-based verdict |
| `matching_rows` | regex matches |
| `plan_type`, `confidence` | filled after extraction |

## ClassificationRegex

Table: `admin_console_classification_regex`

| Column | Notes |
|---|---|
| `kind` | `keyword` / `number` |
| `pattern` | validated regex |
| `is_active`, `description` | |

Unique active pattern.

## PlanRecord

Table: `admin_console_plan_record`

| Column | Notes |
|---|---|
| `link_id`, `table_id`, `classification_id` | provenance |
| `plan_type` | schema key |
| `natural_key` | stable identity within a link |
| `values` | schema-keyed data only |
| `confidence`, `prompt_version` | |

Constraint: unique `(link, natural_key)` among active rows.

## PlanExclusion

Table: `admin_console_plan_exclusion`

| Column | Notes |
|---|---|
| `link_id`, `fingerprint` | unique |
| `plan_type`, `plan_name`, `price_amount` | operator-visible identity |

## SemanticLabel

Table: `admin_console_semantic_label`

Optional LLM label for a table or column, with `provider`, `model`, `language`.

## ReplayRun / ChangeRecord

- `admin_console_replay_run`: `link`, `state`, `scheduled_for`, `started_at`,
  `finished_at`, `before_trace`, `after_trace`, `diff_summary`, `reextracted`, stats,
  `failures`.
- `admin_console_change_record`: `replay_run`, `change_kind` (`content`/`structural`),
  `touches_price_table`, `classification`, `summary`.

## FailureAlert

Table: `admin_console_failure_alert`

| Column | Notes |
|---|---|
| `link_id`, `state` | `open` / `resolved` |
| `failure_rate`, `raised_at`, `resolved_at` | |

## LlmCostLedger

Table: `admin_console_llm_cost_ledger`

| Column | Notes |
|---|---|
| `scope`, `period` | `global`; `daily` / `monthly` / `total` |
| `token_budget` | nullable |
| `tokens_used`, `amount` | spend rows |
| `stage` | `schema_extraction` / `labeling` |
| `link_ref`, `links`, `table_ref` | attribution |
| `idempotency_key` | unique among active rows |
