# admin_console — Workflow

## 1. Approval queue

```text
GET /api/v1/ops/approvals
  → CompaniesInterface.companies_awaiting_verification()
      non-archived, verification_status=pending, oldest first
  → pending_approval_payload(company)
      includes duplicate-domain warning and duplicate ids
```

Duplicate detection is advisory; the operator decides.

## 2. Verification decision

```text
POST /api/v1/ops/companies/{company_id}/verification-decisions
  → operator caller
  → services.record_decision(company_id, actor, outcome, note)
      → CompaniesInterface.record_verification_decision
      → approved: onboard/resume site + enqueue pipeline
      → not_approved: suspend site
  → return company, decision, site
```

## 3. Site management

```text
GET  /ops/sites
  → list sites with company name, link count, stage counts

POST /ops/sites
  → body {company_id}
  → PipelineInterface.onboard_site

GET  /ops/sites/{site_id}
  → site + links

POST /ops/sites/{site_id}/discover-links
  → optional max_pages/max_depth bounds
  → discover_and_store_links

GET/POST /ops/sites/{site_id}/links
  → list links or add manual links
```

## 4. Capture

```text
POST /ops/links/{link_id}/captures
  → start_capture(link, duration_ms)

GET /ops/links/{link_id}/captures/list
  → capture sessions

POST /ops/captures/{capture_session_id}/fail
  → manually mark a session failed
```

## 5. Extraction and classification

```text
POST /ops/links/{link_id}/extractions
  → extract_link_tables

GET /ops/links/{link_id}/tables
  → table payload

GET/POST /ops/links/{link_id}/classifications
  → classify_tables_for_link

GET /ops/plan-schema
  → supported plan types and fields
```

## 6. Plans and labeling

```text
GET/POST /ops/links/{link_id}/plans
  → list plans or run process_link_tables

POST /ops/links/{link_id}/plans/{plan_id}/ignore
  → set_plan_excluded

POST /ops/links/{link_id}/labeling
  → label_link_tables

POST /ops/links/{link_id}/publish
  → publish_link_plans + retire_missing_plans
```

## 7. Replay, alerts, rerun

```text
GET  /ops/replay-runs
  → recent replay runs, optional link/state filters

POST /ops/replay-runs/create
  → enqueue replay for explicit link ids or all due links of a site

GET  /ops/links/{link_id}/failure
  → failure rate, window, threshold, alert state

GET  /ops/alerts
  → open/resolved alerts

POST /ops/links/{link_id}/rerun
  → reset link to a resumable stage
  → enqueue site pipeline for that link at max priority
```

## 8. Settings, budget, metrics

```text
GET/PUT /ops/settings
  → read or update constance values

GET/PUT /ops/llm-token-budget
  → read budget status or set a new budget

GET /ops/metrics
  → links total/published/awaiting budget/dead-lettered,
    open alerts, published records, LLM tokens used
```

## 9. Task backend failure

```text
enqueue raises TaskBackendUnavailable
  → transaction rollback
  → 503 task_backend_unavailable
```
