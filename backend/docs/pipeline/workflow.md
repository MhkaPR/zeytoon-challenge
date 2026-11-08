# pipeline — Workflow

## 1. Site onboarding

```text
onboard_site(company_id, actor)
  → get_or_create Site(company, domain=company.domain)
  → maintenance_state=onboarding, onboarded_at=now
  → emit ops_site_onboarded
```

The operator console calls this after an approved verification decision.

## 2. Link discovery

```text
discover_and_store_links(site)
  → for each configured query (fa/en):
      crawl4ai AdaptiveCrawler(strategy="statistical")
  → apply_link_policy:
      http/https only
      same host when host is given
      deny extensions (js/css/pdf/images/archives/...)
      deny path segments (login/privacy/about/...)
      dedupe, cap at LINK_DISCOVERY_MAX_LINKS
  → get_or_create Link(site, url_hash)
  → site.last_discovered_at=now
  → emit ops_links_discovered; emit ops_empty_discovery when nothing survives
```

Manual links use the same policy with no host restriction.

## 3. Capture

```text
start_capture(link)
  → require review_state == kept
  → reject if a non-terminal capture session exists
  → CaptureSession(recording, duration=CAPTURE_FIXED_DURATION_MS)
  → domtrack capture_headless(url, duration, nav_timeout)
  → save trace bytes through artifacts.save_trace()
  → transaction:
      Trace(storage_key, backend, sha256, valid)
      session=stored, link.current_trace=trace, stage=captured
  → emit ops_trace_stored

on failure:
  → session=failed, error recorded, emit ops_capture_failed
```

## 4. Table extraction

```text
extract_link_tables(link)
  → require current_trace
  → materialize trace to a temp file
  → domtrack extract_tables(min_rows, min_cols, dedupe)
  → replace existing ExtractedTable rows for the link
  → tables found: stage=extracted
  → none:        stage=flagged, emit ops_extraction_empty
```

## 5. Classification and extraction

```text
process_link_tables(link)
  → classify_tables_for_link:
      TableClassifier uses admin regexes
      persist TableClassification(is_price_table, matching_rows)
      none accepted → stage=no_price_tables
  → for each accepted table:
      label_link_tables (LLM pass 1)
      infer_and_extract_plans (LLM pass 2, schema-validated)
      normalize price scale from the source row
      drop incomplete/duplicate plans
      persist PlanRecord(link, table, classification, natural_key, values)
  → plans found: stage=plans_extracted
  → no plans but tables processed: raise NoPlanRecordsError
```

LLM calls use idempotency keys such as `schema-extraction:{link}:{table}`.

## 6. Publishing

```text
publish_link_plans(link)
  → for each PlanRecord:
      skip incomplete plans
      skip operator-excluded fingerprints
      CatalogInterface.upsert_published_record(...)
  → stage=published
  → emit ops_published

retire_missing_plans(link, current_keys)
  → retire published natural keys no longer present
```

## 7. Replay and alerts

```text
execute_replay_run(link)
  → create ReplayRun(running)
  → domtrack compare_replay(before_trace, after recording)
  → store after trace
  → classify changes: content vs structural
  → if changes touch a price table:
      re-extract tables, process plans, publish, retire missing
  → persist ChangeRecord rows
  → run=succeeded, link.last_replay_at=now
  → recompute_failure_rate()
      failure_rate = failed runs / trailing window
      >= FAILURE_RATE_THRESHOLD → open FailureAlert
      < threshold              → resolve open alert
```

## 8. Task orchestration

```text
run_site_pipeline_task(site_id, discover=True, link_id=None)
  → optionally discover once
  → select active links not in terminal stages
  → for each kept link:
      discovered → start_capture
      captured   → extract_link_tables
      extracted  → process_link_tables
      plans_extracted → publish_link_plans + retire_missing_plans
  → mark pipeline_task_state completed/failed
```

## 9. Recovery

```text
recover_site_pipeline_tasks()
  → requeue interrupted RUNNING tasks
  → reset their links to queued
  → fail stale non-terminal capture sessions when no task owns the site
  → reset stale plans_extracted links to extracted
  → clear synthetic pipeline_incomplete markers on resumable links
  → enqueue sites with unfinished links
```

## 10. Operator rerun

```text
rerun_link_stages(link)
  dead_lettered      → captured (if trace) or discovered
  no_price_tables    → extracted
  awaiting_llm_budget→ extracted (or discovered for unknown stage)
  clear error/retry count
  enqueue site pipeline for that link
```
