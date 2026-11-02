# Contract: domtrack and crawl4ai Integration (FR-000, FR-000a, FR-000b, FR-000c, SC-020)

This feature MUST use the `domtrack` library as-is for every capability it already provides
and MUST NOT reimplement any of them, and MUST use `crawl4ai` for adaptive link discovery.
This contract states **which capability each pipeline stage calls, from where, and what it
returns**. It is the auditable form of FR-000 and SC-020.

## Reuse rule

- Every `import domtrack...` in the backend lives in exactly one module:
  `backend/src/admin_console/domtrack_client.py`.
- Every `import crawl4ai...` in the backend lives in exactly one module:
  `backend/src/admin_console/discovery.py`.
- A pytest test (`admin_console/tests/test_domtrack_reuse.py`) walks the backend source tree
  and fails if `domtrack` is imported outside `domtrack_client.py` or if `crawl4ai` is
  imported outside `discovery.py`, so SC-020 is locked by a test rather than by review.
- No stage may parse, transform, or re-derive what domtrack or crawl4ai return; results are
  stored as the libraries produced them. In particular the feature produces no selector/formula
  recipe: plan extraction returns **data** from the LLM against the code-defined schema
  (FR-028), and domtrack's own column identifiers are stored as-is for provenance only.

## Where each capability runs

Every stage runs **server-side**. No stage requires an operator machine, a headed browser, or
an operator's local domtrack installation (FR-000c).

| Pipeline stage | Capability | Invocation site | Transport |
| --- | --- | --- | --- |
| Adaptive link discovery | `crawl4ai` `AsyncWebCrawler` + `AdaptiveCrawler` (`AdaptiveConfig(strategy="statistical")`) | Server | Python library (only in `discovery.py`) |
| Deterministic link policy | This feature (same-host, deny lists, dedupe) | Server | Python (no crawl4ai/domtrack call) |
| Link refilter input extraction | This feature (`refilter.py`: URL + `h1–h3` + important section) | Server | Python + `httpx` (no LLM) |
| Link refilter / classification / plan extraction | OpenAI-compatible LLM (`llm.py`) | Server | HTTPS to the configured gateway |
| Capture / record a link | `domtrack capture` (`Recorder`, `CaptureSession`, `TracerConfig`, `headless=True`) | Server | Python library |
| Replay a stored trace | `domtrack replay` (`Replayer`, `ReplayConfig`) | Server | Python library |
| Record the replayed page | `domtrack replay --record` (`RecordingConfig(enabled=True, ...)`) | Server | Python library |
| Compare before/after (replay + record + diff) | `domtrack compare` (`compare_replay`) | Server | Python library |
| Content diff of two traces | `domtrack diff` (`diff_traces`, `DiffResult`) | Server | Python library |
| Inspect a trace's DOM | `domtrack html` (`rebuild_html`, `DomState`) | Server | Python library (operator diagnostics) |
| Table extraction | `domtrack tables extract` (`discover_tables`, `DiscoveryConfig`) | Server | Python library |
| Table labeling | `domtrack tables label` (`label_tables`, `LabelConfig`) | Server | Python library |
| Table display/export | `domtrack tables show` | Server | Python library (optional rendering for review/exports) |
| REST endpoint | `domtrack serve` (FastAPI) | Server | Available for diagnostics/integration only; the pipeline calls the Python library |

There is no dubbing-out layer: the console calls these functions directly (through the
single adapter module per library) and stores what they return. `domtrack compare` is the one
call that performs replay, record-during-replay, and diff together (FR-039); the pipeline does
not stitch those three stages itself.

## Adapter surface

### `admin_console/domtrack_client.py` (only domtrack importer)

| Adapter function | domtrack call it wraps | Returns |
| --- | --- | --- |
| `capture_headless(url, duration_ms, nav_timeout_ms)` | `domtrack` `Recorder`/`CaptureSession` with `headless=True`; navigates, waits for settle, scrolls to bottom, records for `duration_ms` | the produced trace path/metadata, or a raised capture error |
| `load_trace(key)` | `domtrack.load_raw` / `domtrack.is_rrweb_trace` | raw trace + validity flag |
| `extract_tables(path, min_rows, min_cols)` | `domtrack.tables.discover_tables(raw, DiscoveryConfig(...))` | domtrack's `{total_candidates, tables_returned, tables}` verbatim |
| `label_tables(tables, label_config)` | `domtrack.tables.labeling.label_tables(data, LabelConfig(...))` | labeled tables, or the provider error |
| `compare_replay(before_path, replay_config, recording)` | `domtrack.compare.compare_replay(...)` | `CompareResult` (`.summary`, `.stats`, `.diff`) |
| `diff_traces(before_path, after_path)` | `domtrack.diff.diff_traces(...)` | `DiffResult` (`.summary`, `.to_dict()`) |
| `rebuild_dom(path, at_record)` | `domtrack.html.rebuild_html(...)` | reconstructed DOM |
| `is_trace(raw)` | `domtrack.is_rrweb_trace(raw)` | `bool` |

### `admin_console/discovery.py` (only crawl4ai importer)

| Adapter function | crawl4ai call it wraps | Returns |
| --- | --- | --- |
| `crawl_candidate_links(seed_domain, query, bounds)` | `AsyncWebCrawler` with `AdaptiveCrawler`/`AdaptiveConfig(strategy="statistical")`; seeds on the company domain and runs Persian + English host/server-plans queries within the configured page bound | the crawler's discovered URLs (harvest) |
| `apply_link_policy(urls, deny_lists)` | This feature (deterministic; no library call) | normalized, same-host, de-duplicated candidate URLs with denied extensions/segments removed |

`crawl_candidate_links` returns **normal HTML** alongside the discovered URLs, so
`refilter.py` can derive the URL, `h1–h3`, and the important section deterministically; the
HTML is never sent to an LLM (FR-012). No crawl4ai behaviour is reimplemented, and no
domtrack capability is routed through crawl4ai (or vice versa).

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
  same object is passed unchanged to replay, compare, diff, and table extraction (SC-009).
  Because the key is UUID-based, the stored name is unique and never collides with another
  capture.
- Every stored trace is validated with domtrack's trace-validity check at store time; a file
  that fails validation is rejected with `code: "invalid_field"` and the link does not
  advance. The result is recorded on the `Trace` row as `is_valid_trace` (the platform does
  not name its field after the trace format).
- The trace is associated with its link and capture time at store time (FR-016). Capture is
  server-side and headless, so no operator is recorded against a trace.

## Configuration surface

| Value | Where it lives | Why |
| --- | --- | --- |
| Adaptive-crawl seed, host/server-plans query (Persian + English), `max_pages`/`max_depth` bounds | constance | Runtime tunables for `AdaptiveConfig`/`AdaptiveCrawler` (FR-008). |
| Deterministic link policy: denied file extensions, denied path segments | constance | Runtime tunables for the deterministic policy (FR-009). |
| Capture `duration_ms` (required headless), `nav_timeout_ms` | constance | Runtime tunables for headless capture (FR-017). |
| Refilter `provider`, `model`, `confidence drop threshold` | constance | Admin-facing runtime tunables for the refilter LLM (FR-013, FR-014, FR-043). |
| Labeling `provider`, `model`, `language`, `batch_size`, `dry_run`, `LABELING_ENABLED` | constance | Admin-facing runtime tunables (FR-021, FR-022, FR-043). |
| Replay `mode` (`clean`), `time_policy`, `speed`, third-party detection settings | constance | Runtime tunables for `ReplayConfig`; `clean` mode and third-party detection keep chat/support widgets from creating false diffs (edge case). |
| LLM gateway `base_url`, `api_key`, and provider (`openai`) | Environment only (`OPENAI_API_KEY`, `OPENAI_BASE_URL`) | Principle III: secrets never in code or the repository; provider is OpenAI (via the gateway base URL) for now. |
| Artifact storage backend (`STORAGES["default"]`, S3-compatible via `django-storages` by default) | `settings.py` (env-overridable) | Developer/devops selects the storage type (S3, local filesystem) without code changes. |
| `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_ENDPOINT_URL`, `AWS_S3_REGION_NAME`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | Environment only | Issue S3 credentials and endpoint (Iran-hosted) from the environment; secrets never in code (Principle III). |
| Retry/backoff and dead-letter thresholds | constance | Runtime tunables for the resilience policy (FR-052). |
| LLM token budget per period | Model-backed (`LlmCostLedger.token_budget`), not constance | Admin owns the budget (FR-047); checked before every LLM-gated call. |

There is no `DOMTRACK_LOCAL_API_URL`, no sitemap timeout, and no capture-mode setting: capture
is always server-side and headless with a fixed duration.

## Failure handling

- Capture: a failed or timed-out capture is retried with backoff; when the retries are
  exhausted the link is **dead-lettered** rather than retried indefinitely, and the error is
  surfaced (FR-018, FR-052). A link does not advance until a valid trace is stored.
- Link discovery: a crawl that yields no candidates keeps the site at `onboarding` and
  informs the operator (FR-011); a crawl/network error is retried with backoff and, if it
  persists, recorded against the site without discarding already-discovered links.
- Extraction: zero tables ⇒ the link is recorded as having no tables; the operator may
  re-capture (edge case, FR-022).
- Replay/compare: domtrack-reported failures are recorded per run and feed the link's failure
  rate; they are never re-derived by the platform (FR-039, FR-053).
- Labeling and every other LLM-gated stage: when the provider is unavailable the call is
  retried with backoff; when the **token budget is exhausted** the call is not made, no
  partial record is written, non-LLM stages continue, and the affected link/run parks in
  `awaiting_llm_budget` until the budget is restored, with the admin notified (FR-047,
  FR-048, SC-016).
- Masking: no failure message, log entry, or alert contains full company phone data or trace
  content (FR-044, SC-021).
