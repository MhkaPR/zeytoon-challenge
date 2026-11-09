# pipeline — Configuration

All values below are django-constance constants editable from Django admin or the operator
settings endpoint. Defaults come from `config/settings/base.py`.

## Replay and alerts

| Constant | Default | Purpose |
|---|---|---|
| `REPLAY_PERIOD_HOURS` | `24` | hours between scheduled replays per link |
| `REPLAY_BATCH_SIZE` | `50` | max links per replay cycle |
| `FAILURE_RATE_THRESHOLD` | `0.5` | failure ratio that opens an alert |
| `FAILURE_RATE_WINDOW_RUNS` | `5` | trailing runs used for the ratio |
| `REPLAY_MODE` | `clean` | domtrack replay mode |
| `REPLAY_SPEED` | `1.0` | replay speed multiplier |
| `REPLAY_TIME_POLICY` | `replay` | domtrack time policy |
| `REPLAY_THIRD_PARTY_DETECTION` | `true` | suppress chat/widget noise |

## Discovery

| Constant | Default | Purpose |
|---|---|---|
| `LINK_CRAWL_QUERY_FA` | Persian query | adaptive crawler query |
| `LINK_CRAWL_QUERY_EN` | English query | adaptive crawler query |
| `LINK_CRAWL_MAX_PAGES` | `60` | pages per run |
| `LINK_CRAWL_MAX_DEPTH` | `5` | crawl depth |
| `LINK_CRAWL_TOP_K` | `50` | top-k links per frontier step |
| `LINK_DENY_EXTENSIONS` | file list | excluded extensions |
| `LINK_DENY_SEGMENTS` | path list | excluded path segments |
| `LINK_DISCOVERY_MAX_LINKS` | `5000` | max stored candidates |

## Capture and tables

| Constant | Default | Purpose |
|---|---|---|
| `CAPTURE_FIXED_DURATION_MS` | `15000` | headless capture length |
| `CAPTURE_NAV_TIMEOUT_MS` | `30000` | navigation timeout |
| `TABLE_DISCOVERY_MIN_ROWS` | `2` | min rows for a table candidate |
| `TABLE_DISCOVERY_MIN_COLS` | `2` | min columns |
| `TABLE_DISCOVERY_DEDUPE` | `true` | domtrack dedupe |

## Labeling and extraction

| Constant | Default | Purpose |
|---|---|---|
| `LABELING_PROVIDER` | `openai` | provider key |
| `LABELING_MODEL` | empty | model override |
| `LABELING_LANGUAGE` | `fa` | label language |
| `LABELING_BATCH_SIZE` | `10` | tables per LLM call |

## Resilience

| Constant | Default | Purpose |
|---|---|---|
| `RETRY_MAX_ATTEMPTS` | `3` | attempts before dead-letter |
| `RETRY_BACKOFF_SECONDS` | `5` | base backoff |
| `PUBLISH_AUTO_THRESHOLD` | `0.0` | confidence threshold for automatic publication |

## Environment variables

| Variable | Purpose |
|---|---|
| `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL` | LLM provider |
| `ARTIFACT_STORAGE_BACKEND` | `s3` or filesystem |
| `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_ENDPOINT_URL`, `AWS_S3_REGION_NAME`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | S3-compatible artifact storage |
| `CRAWLER_USER_AGENT` | transparent crawler identity |
| `CRAWLER_REQUEST_DELAY_SECONDS` | request delay |
| `PRICE_TABLE_MIN_MATCHING_ROWS` | minimum regex-matching rows |

## Commands

```bash
# run a database-backed task worker
cd backend/src && python manage.py db_worker

# enqueue scheduled replays
cd backend/src && python manage.py run_scheduled_replays
```
