# Contract: domtrack Integration (FR-000, FR-000a, FR-000b, SC-017)

This feature MUST use the `domtrack` library as-is for every capability it already provides
and MUST NOT reimplement any of them. This contract states **which domtrack capability each
pipeline stage calls, from where, and what it returns**. It is the auditable form of FR-000
and SC-017.

## Reuse rule

- Every `import domtrack...` in the backend lives in exactly one module:
  `backend/src/admin_console/domtrack_client.py`. A pytest test
  (`admin_console/tests/test_domtrack_reuse.py`) walks the backend source tree and fails if
  `domtrack` is imported anywhere else, so SC-017 is locked by a test rather than by review.
- No stage may parse, transform, or re-derive what domtrack returns; results are stored as
  domtrack produced them, and the conversions the platform needs (recipe formulas over
  column selectors) operate on domtrack's own identifiers (`path`, `column_id`), never on a
  substitute structure created by this feature.

## Where each capability runs

| Pipeline stage | domtrack capability | Invocation site | Transport |
| --- | --- | --- | --- |
| Capture / record a link | `domtrack capture` (`Recorder`, `CaptureSession`, `TracerConfig`) | Operator's machine | Local REST API `POST /capture` on `DOMTRACK_LOCAL_API_URL` (called by `POST /api/v1/ops/links/{id}/captures`); the CLI is an accepted alternative |
| Replay a stored trace | `domtrack replay` (`Replayer`, `ReplayConfig`) | Server | Python library |
| Record the replayed page | `domtrack replay --record` (`RecordingConfig(enabled=True, ...)`) | Server | Python library |
| Compare before/after (replay + record + diff) | `domtrack compare` (`compare_replay`) and `domtrack diff` | Server | Python library |
| Content diff of two traces | `domtrack diff` (`diff_traces`, `DiffResult`) | Server | Python library |
| Inspect a trace's DOM | `domtrack html` (`rebuild_html`, `DomState`) | Server | Python library (operator diagnostics) |
| Table extraction | `domtrack tables extract` (`discover_tables`, `DiscoveryConfig`) | Server | Python library |
| Table labeling | `domtrack tables label` (`label_tables`, `LabelConfig`) | Server | Python library |
| Table display/export | `domtrack tables show` | Server | Python library (optional rendering for review/exports) |
| Local capture endpoint | `domtrack serve` (FastAPI) | Operator's machine | The endpoint the console's capture button calls |

There is no dubbing-out layer: the console calls these functions directly (through the
single adapter module) and stores what they return.

## Adapter surface (`admin_console/domtrack_client.py`)

The adapter is deliberately small and typed, keeping each call as close to domtrack as
possible:

| Adapter function | domtrack call it wraps | Returns |
| --- | --- | --- |
| `start_local_capture(url, mode, duration_ms=None)` | HTTP `POST /capture` on the local server | `{local_trace_path, mutation_count, event_count}` or a `domtrack_unreachable` error |
| `load_trace(key)` | `domtrack.load_raw` / `domtrack.is_rrweb_trace` | raw trace + validity flag |
| `extract_tables(path, min_rows, min_cols)` | `domtrack.tables.discover_tables(raw, DiscoveryConfig(...))` | domtrack's `{total_candidates, tables_returned, tables}` verbatim |
| `label_tables(tables, label_config)` | `domtrack.tables.labeling.label_tables(data, LabelConfig(...))` | labeled tables, or the provider error |
| `compare_replay(before_path, replay_config, recording)` | `domtrack.compare.compare_replay(...)` | `CompareResult` (`.summary`, `.stats`, `.diff`) |
| `diff_traces(before_path, after_path)` | `domtrack.diff.diff_traces(...)` | `DiffResult` (`.summary`, `.to_dict()`) |
| `rebuild_dom(path, at_record)` | `domtrack.html.rebuild_html(...)` | reconstructed DOM |
| `is_trace(raw)` | `domtrack.is_rrweb_trace(raw)` | `bool` |

domtrack's library API works with local filesystem paths, while the platform stores traces as
objects under UUID keys (S3 by default). The adapter bridges this without changing domtrack:
`artifacts.py` materializes a stored object to a temporary local file for the duration of a
domtrack call and streams results back to the store on write. The `*_path` parameters above
are therefore local paths produced by that materialization step, not the platform's storage
keys; no domtrack capability is reimplemented by this bridging.

## Trace file contract

- The stored artifact is **domtrack's native trace file** (`{"meta", "snapshot", "records",
  "events"}`). It is written through Django's `STORAGES` API (`admin_console/artifacts.py`)
  to the configured backend — **S3-compatible object storage by default**, switchable to
  local filesystem or another alias from settings — under a **UUID-based object key**
  (`traces/<uuid4>.json`), and referenced by key and hash from the `Trace` row (FR-000a).
  The database never stores the trace body. No conversion step exists in the pipeline; the
  same object is passed unchanged to replay, compare, diff, and table extraction (SC-007).
  Because the key is UUID-based, the stored name is unique and never collides with another
  capture or reveals the operator's local path.
- Every stored trace is validated with domtrack's trace-validity check at store time; a file
  that fails validation is rejected with `code: "invalid_field"` and the link does not
  advance. The result is recorded on the `Trace` row as `is_valid_trace` (the platform does
  not name its field after the trace format).
- The trace is associated with its link, capturing operator, and capture time at store time
  (FR-016).

## Configuration surface

| Value | Where it lives | Why |
| --- | --- | --- |
| `DOMTRACK_LOCAL_API_URL` | `settings.py` (env-overridable) | Operator-machine endpoint; differs per operator and the default port can collide with the dev server. |
| Artifact storage backend (`STORAGES["default"]`, S3-compatible via `django-storages` by default) | `settings.py` (env-overridable) | Developer/devops selects the storage type (S3, local filesystem) without code changes. |
| `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_ENDPOINT_URL`, `AWS_S3_REGION_NAME`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | Environment only | Issue S3 credentials and endpoint (Iran-hosted) from the environment; secrets never in code (Principle III). |
| `SITEMAP_FETCH_TIMEOUT_SECONDS` | constance | Runtime tunable for discovery (adjacent to domtrack). |
| Capture modes allowed, `duration_ms` default | constance | Runtime tunable (FR-013, FR-043). |
| Table discovery `min_rows`, `min_cols`, `dedupe` | constance | Runtime tunable for `DiscoveryConfig`. |
| Labeling `provider`, `model`, `language`, `batch_size`, `dry_run`, `LABELING_ENABLED` | constance | Admin-facing runtime tunables (FR-021, FR-022, FR-043). |
| Replay `mode` (`clean`), `time_policy`, `speed`, third-party detection settings | constance | Runtime tunables for `ReplayConfig`; `clean` mode and third-party detection keep chat/support widgets from creating false diffs (edge case). |
| Provider API keys (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY`) | Environment only | Principle III: secrets never in code or the repository. |

## Failure handling

- Capture: local domtrack unreachable ⇒ `502 domtrack_unreachable`; the link does **not**
  advance (FR-017).
- Extraction: zero tables ⇒ the link is flagged; the operator may re-capture, possibly with a
  different observed subtree (edge case, FR-020).
- Replay/compare: domtrack-reported failures are recorded per run and feed the link's failure
  rate; they are never re-derived by the platform (FR-038, FR-040).
- Labeling: provider unavailable or ceiling reached ⇒ labeling is skipped/reported and every
  other stage continues unaffected (FR-023, FR-024).
