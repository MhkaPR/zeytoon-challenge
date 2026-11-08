# Backend Workflows

This document describes the main end-to-end flows across the backend. Per-app details are
in each app's `workflow.md`.

## 1. HTTP request lifecycle

```text
Client
  │
  ▼
config.urls → config.api.urls → config.api.v1.urls → app urls.py
  │
  ▼
ViewSet (views/v1)
  │  resolve caller from Bearer JWT (when required)
  │  validate input with serializers/v1 (parse_input)
  ▼
service (write) or selector (read)
  │  business rules, transactions, domain events
  ▼
models / external clients (domtrack, crawl4ai, LLM, SMS)
  │
  ▼
serializer → Response
```

Errors raised as `ApiError` (or DRF exceptions) are normalized by
`apps.accounts.exceptions.api_exception_handler` into the shared error envelope.

## 2. Authentication flow

```text
POST /api/v1/auth/otp/request
  → normalize phone
  → reject blocked user / active lockout
  → generate code, store HMAC hash + expiry in Redis
  → send through configured SMS gateway

POST /api/v1/auth/otp/verify
  → normalize phone
  → check lockout / blocked user
  → compare HMAC code
  → on success: delete code, clear lockout
  → get_or_create user by phone (implicit signup)
  → merge anonymous recommendation profile into the account
  → issue access + refresh tokens
  → set refresh cookie
  → resolve safe return URL

POST /api/v1/auth/token/refresh
  → read refresh cookie
  → rotate + blacklist old refresh
  → issue new access token and refresh cookie

POST /api/v1/auth/logout
  → blacklist refresh token
  → clear visitor recommendation state
  → delete refresh and visitor cookies
```

See [`accounts/workflow.md`](accounts/workflow.md) for lockout and rate-limit details.

## 3. Company onboarding flow

```text
User creates a company
  → Company(status=pending, charge=not_charged)
  → step rows seeded: company_information=approved, verification=locked

Operator reviews the approval queue
  → approved:
      append VerificationDecision
      company.verification_status = verified
      verification step = approved
      pipeline site onboarded or resumed, pipeline enqueued
  → not_approved:
      append VerificationDecision
      company.verification_status = rejected
      company_information step reopened, verification step locked

Verified + charged company
  → plan eligibility allowed
  → crawl can be enabled
```

Ownership transfer is always refused in-product and handled manually by an admin.
Companies are archived, never hard-deleted.

## 4. Automated site pipeline flow

```text
Site onboarding (operator approval or manual)
  → discover links with crawl4ai adaptive crawler
  → apply deterministic same-host/deny-list policy
  → persist Link(pipeline_stage=discovered)

Per link, resumed from persisted stage:
  discovered
    → server-side headless capture (domtrack)
    → store trace artifact + Trace row
    → captured
  captured
    → extract tables (domtrack)
    → extracted
  extracted
    → rule-based price-table classification
    → label tables + schema-extract plan data (LLM, budget-gated)
    → plans_extracted
  plans_extracted
    → publish complete, non-excluded plans to catalog
    → published

Scheduled replay:
  → replay + record + diff against the current trace
  → classify content vs structural changes
  → re-extract/publish when needed
  → update failure rate and open/resolve alerts
```

LLM stages park the link in `awaiting_llm_budget` when the token budget is exhausted.
Provider/network failures retry with backoff and dead-letter the link on exhaustion.

## 5. Catalog and recommendation flow

```text
GET /api/v1/catalog/plans
  → filter PublishedRecord(is_published=True)
  → if sort is price/expensive/relevance: deterministic ordering
  → otherwise: rank the filtered set via RecommendationsInterface
  → paginate after ranking so pages never repeat
  → enrich with site/company identity and source URL

GET /api/v1/catalog/plans (page extra)
  → facets: companies, operating systems, locations, normalized resources

POST /api/v1/recommendations/signals
  → validate kind + plan ids
  → resolve visitor or user profile
  → update interest clusters using the cached plan space
  → append an InterestSignal
```

Ranking is cold-start safe: a viewer without a profile is compared against the plan-space
prior, so ordering is deterministic.

## 6. Operator console flow

```text
GET  /api/v1/ops/approvals
POST /api/v1/ops/companies/{id}/verification-decisions
  → CompaniesInterface records the decision
  → PipelineInterface onboards/resumes or suspends the site
  → pipeline task enqueued on approval

Site/link operations
  → discover links, add manual links, start/fail capture
  → extract tables, classify, label, extract plans
  → ignore a plan, publish, inspect replay runs and alerts
  → rerun a link from its persisted stage

Settings/observability
  → read/update constance values
  → read/update LLM token budget
  → read metrics snapshot
```

## 7. Background task and recovery flow

```text
run_site_pipeline_task(site_id, discover=...)
  → discover once when requested
  → iterate active links not in terminal stages
  → advance each link through capture → extraction → plans → publish
  → mark pipeline_task_state queued/running/completed/failed

recover_site_pipeline_tasks()
  → requeue interrupted RUNNING tasks
  → mark stale non-terminal capture sessions failed
  → reset stale plans_extracted links to extracted
  → enqueue sites with resumable links
```

## 8. Adding a feature

1. Put the model under `apps/<app>/models/` and inherit `TimestampedModel`.
2. Put write logic in `services/v1/` and read logic in `selectors.py`.
3. Add versioned serializers and a ViewSet action.
4. Expose cross-app behavior only through `interfaces.py`.
5. Add runtime-tunable values to `CONSTANCE_CONFIG`.
6. Emit a structured event from `events.py` for operator-visible transitions.
7. Add tests under `apps/<app>/tests/` and update these docs.
