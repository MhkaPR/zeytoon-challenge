# pipeline — Architecture

## 1. Responsibility

`apps.pipeline` is the automated site-maintenance engine. It owns:

- adaptive link discovery;
- server-side headless capture via domtrack;
- trace artifact storage;
- table extraction and rule-based price-table classification;
- optional LLM labeling and schema-based plan extraction;
- publishing/retiring catalog records;
- replay, diffing, failure rates, and alerts;
- Django Tasks orchestration and worker recovery.

Every stage is server-side and per-link isolated.

## 2. Internal layout

| Path | Responsibility |
|---|---|
| `models/site.py` | `Site` (one per approved company) |
| `models/link.py` | `Link`, review state, pipeline stage |
| `models/capture.py` | `CaptureSession` |
| `models/trace.py` | trace metadata (body lives in object storage) |
| `models/table.py` | extracted tables/columns/rows |
| `models/classification.py` | `TableClassification` |
| `models/regex.py` | admin-managed classification regexes |
| `models/plan.py` | `PlanRecord` |
| `models/exclusion.py` | operator plan exclusions |
| `models/semantic_label.py` | optional LLM labels |
| `models/replay.py` | `ReplayRun`, `ChangeRecord` |
| `models/alert.py` | `FailureAlert` |
| `models/cost_ledger.py` | LLM token budget/spend |
| `discovery.py` | crawl4ai adaptive discovery + deterministic policy |
| `domtrack_client.py` | domtrack capture/extract/label/compare/diff wrapper |
| `artifacts.py` | trace save/open/materialize/delete through Django storage |
| `table_classifier.py` | regex-based price-table detection |
| `plan_schema.py` | code-defined plan schema and Pydantic models |
| `llm.py` | OpenAI-compatible client, budget gate, structured extraction |
| `replay.py` | replay + record + diff + change classification |
| `tasks.py` | Django Tasks bodies and recovery |
| `services/v1/pipeline.py` | stage orchestration and operator reads |
| `interfaces.py` | `PipelineInterface` |
| `events.py` | structured pipeline events |
| `constants.py` | constance-backed tunables |

## 3. Stage machine

`Link.pipeline_stage`:

```text
discovered
  → captured
  → extracted
  → plans_extracted
  → published

side states:
  no_price_tables
  awaiting_llm_budget
  flagged
  dead_lettered
```

`Link.pipeline_task_state` tracks task ownership (`idle`, `queued`, `running`,
`completed`, `failed`).

## 4. External integrations

| Integration | Module | Notes |
|---|---|---|
| crawl4ai | `discovery.py` | only module importing crawl4ai; statistical strategy, no embeddings/LLM |
| domtrack | `domtrack_client.py` | headless capture, table extraction, labeling, replay/diff |
| OpenAI-compatible LLM | `llm.py` | structured outputs, budget-gated |
| object storage | `artifacts.py` | S3-compatible or filesystem via `STORAGES` |

## 5. Budget and resilience

- Every LLM call is gated by `LlmBudget`; exhausted budget raises
  `LlmBudgetExhausted` and parks the link in `awaiting_llm_budget`.
- `_run_with_retries()` retries provider/network failures with linear backoff and
  dead-letters the link on exhaustion.
- A failed refresh of the recommendation space is unrelated; pipeline budget failures never
  write partial ledger rows.

## 6. Interfaces

`PipelineInterface` exposes:

- site/link/capture lookups and summaries;
- public site identity, link URLs, and recent companies for `catalog`;
- site onboarding/suspension/resume and task enqueue for `admin_console`;
- operator-only guards (`_require_operator`).

It exposes opaque ids and summaries, not ORM internals.
