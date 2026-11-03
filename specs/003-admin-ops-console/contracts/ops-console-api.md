# Contract: Operator Console API (v1)

Base path: `/api/v1/ops`. The console lives at `/ops` in the frontend (deliberately not
`/admin`, which is Django's built-in admin site) and this is its API prefix. Everything the
operator console does — the approval queue, site onboarding, link discovery and refilter,
server-side capture, table extraction, table classification, plan-schema extraction,
optional labeling, publishing, replay and change detection, alerts, and settings — is served
from this prefix. This contract is the reviewed source of intent; the generated OpenAPI
schema (drf-spectacular) is the machine-readable form.

Two concerns are **not** owned by this module and appear here only as the call the console
makes on the caller's behalf: published plan records are written by the `catalog` app through
its interface, and notifications are delivered by the `notifications` app through its
interface (see sections 9 and 10).

Company **verification** is recorded by delegating to `companies` (see the feature-002
contract for the canonical decision semantics). The `admin_console` decision endpoint is a
thin console facade over `CompaniesInterface.record_verification_decision`; there is still
exactly one append-only `VerificationDecision` record per decision (FR-002, FR-006, SC-001).

The pipeline is **fully automated**: the operator no longer maps columns, writes formulas, or
cleans data. There is **no recipe, no formula engine, no Handsontable workspace, and no
cleaning stage**; plan data is produced directly by the LLM against a single code-defined
schema. The operator's job is approval, control of the tunables and token budget, and review
of what the automation produced.

## Conventions

- Authentication: `Authorization: Bearer <access_token>` on every endpoint here (JSON Web
  Token auth from the `accounts` feature, Principle XI). Unauthenticated requests get `401`.
- Authorization: every endpoint requires an operator role — membership in the `ops` group
  or the `admin` group (a superuser is an admin). `ops` grants only this console; `admin`
  additionally grants Django `/admin`. A non-operator caller gets `403` with
  `code: "admin_required"` (FR-001, FR-005). A company owner can never reach a decision,
  capture, or maintenance endpoint (FR-005, SC-004). Setting the token budget requires the
  `admin` role (Principle II).
- CSRF: state-changing requests MUST include `X-CSRFToken` matching the CSRF cookie.
- Phone numbers: the approval queue returns the company phone number in full. No response
  or log includes trace content (FR-055, SC-021).
- Idempotency: `GET` endpoints are side-effect free; discovery, refilter, capture, extraction,
  classification, plan extraction, replay, and notification dispatch are explicitly guarded
  against duplicate execution (documented per endpoint). A retried LLM call is guarded by an
  idempotency key and is not charged twice (FR-050).
- Budget state: when the LLM token budget is exhausted, a request that needs the LLM returns
  `202` with `code: "awaiting_llm_budget"`; no partial row is written and the work resumes
  automatically when the budget is restored (FR-048).

### Error shape

```json
{
  "error": {
    "code": "plans_required",
    "message": "This table was not classified as a plans table, so no plan data was extracted.",
    "fields": { "classification_id": 55 }
  }
}
```

Error codes used by this contract: `admin_required`, `not_authenticated`, `not_found`,
`invalid_field`, `link_not_ready`, `trace_required`, `capture_in_progress`, `crawl_failed`,
`no_tables_found`, `plans_required`, `labeling_disabled`, `awaiting_llm_budget`,
`site_suspended`, `dead_lettered`, `alerts_configured_recipient_exists`.

There is no `recipe_incomplete`, `domtrack_unreachable`, or `llm_ceiling_exceeded`: mapping is
retired, domtrack runs server-side, and the LLM is gated by a token budget that parks work
rather than failing it.

## 1. Approval queue (FR-001..FR-006)

### GET /api/v1/ops/approvals

List companies awaiting verification with the information needed to decide.

**Response 200**

```json
{
  "results": [
    {
      "company_id": 42,
      "company_name": "Example Hosting",
      "representative_name": "Ali Rezaei",
      "domain": "example.com",
      "phone_number": "02123456789",
      "registered_at": "2026-10-20T09:12:00Z",
      "duplicate_domain_warning": true,
      "duplicate_of": [17]
    }
  ],
  "count": 1
}
```

`duplicate_domain_warning` is advisory only: the system MUST NOT auto-reject or auto-merge;
resolution stays with the operator (FR-004).

### POST /api/v1/ops/companies/{company_id}/verification-decisions

Record exactly one outcome for a company review; delegates to the `companies` decision
service so the append-only record keeps its single owner.

**Request**

```json
{ "outcome": "approved", "note": "Domain verified by phone call." }
```

`outcome` is `approved` or `not_approved`.

**Responses**

| Status | Meaning | Body |
|--------|---------|------|
| 201 | Decision recorded | `{ "company": { "id", "verification_status", "verified": true }, "decision": { "outcome", "actor_id", "decided_at", "note" } }` |
| 400 | Unknown outcome, or missing note where required | error `code: "invalid_field"` |
| 403 | Caller is not an operator, or is the company owner | error `code: "admin_required"` (FR-005) |
| 404 | Company not found | error `code: "not_found"` |

**Effects**: `approved` ⇒ company verified, full panel reachable, its `Site` created in
`onboarding` and the maintenance lifecycle started, and automated link discovery enqueued
(FR-003). `not_approved` ⇒ company stays unverified, step one reopens, and its `Site` is
suspended (FR-003, edge case).

## 2. Automated link discovery (FR-007..FR-011)

Link discovery replaces sitemap discovery entirely. The system crawls the site domain with
crawl4ai's **adaptive crawler using the statistical strategy** (keyword/BM25 statistics only —
no embeddings, no LLM) and a configured host/server-plans query, then reduces the harvest
with a deterministic policy (FR-008, FR-009, SC-005).

### POST /api/v1/ops/sites

Onboard the company's single site. Sitemap fields are gone; the domain is the adaptive-crawl
seed.

**Request**: `{ "company_id": 42 }`

**Responses**

| Status | Meaning | Body |
|--------|---------|------|
| 201 | Site onboarded | `{ "site": { "id", "domain", "maintenance_state": "onboarding" } }` |
| 409 | Company already has a site | error `code: "invalid_field"`, `fields: {"company_id": "already onboarded"}` (FR-007) |
| 403 | Company is not approved/verified | error `code: "link_not_ready"` |

### POST /api/v1/ops/sites/{site_id}/discover-links

Run the adaptive crawl for the site's domain and store the surviving links as `candidate`
links with `source: "adaptive_crawl"`. Idempotent on `(site, url_hash)`. Honors robots.txt,
uses the transparent user-agent, and rate-limits per domain (Principle X).

**Request (optional)**: `{ "query": "hosting plans", "max_pages": 60, "max_depth": 3 }` — any
omitted field falls back to the configured tunable (FR-008, FR-054).

**Response 200**

```json
{
  "site": { "id": 7, "domain": "example.com" },
  "discovered": 128,
  "after_policy": 41,
  "candidates": [ { "id": 901, "url": "https://example.com/hosting/basic", "source": "adaptive_crawl" } ]
}
```

`discovered` is the raw harvest; `after_policy` is the count that survived the deterministic
policy (same-host only; fragments removed; query strings stripped; denied file extensions
such as scripts, stylesheets, text, JSON/XML, documents, media, and fonts removed; denied
path segments such as blog, docs, support, auth, cart, and legal pages removed; deduplicated
and normalized). Non-HTML resources never advance (FR-009, SC-006).

When the crawl yields no candidates, `discovered=0` and the site stays at `onboarding`; the
operator is informed (FR-011). When the crawl itself fails, the request returns `502` with
`code: "crawl_failed"` and the site is unchanged.

### POST /api/v1/ops/sites/{site_id}/links

Enter links manually (edge case only; adaptive crawl is the default source).

**Request**: `{ "urls": ["https://example.com/hosting/pro", "https://example.com/vps"] }`

**Response 201**: the created `candidate` links with `source: "manual"`.

### GET /api/v1/ops/sites/{site_id}/links?review_state=candidate

List links for the site with their discovery state, refilter verdict, stage, and budget state.
Links are grouped by review state; a link is never hard-deleted (removal is a recorded state).

## 3. LLM link refilter (FR-012..FR-015)

For each candidate link, the system deterministically derives, **without an LLM**, the link
URL, its `h1–h3` headings, and its important section — the largest text-density block inside
`<main>` or `<article>` — from the normal HTML the crawler returned. Only that summary is sent
to the LLM; **page HTML is never sent to the model** (FR-012, SC-007).

### POST /api/v1/ops/links/{link_id}/refilter

Run (or re-run) the refilter for a candidate link.

**Request (optional)**: `{ "force": false }`

**Responses**

| Status | Meaning | Body |
|--------|---------|------|
| 200 | Verdict recorded | `{ "link": { "refilter_state": "kept", "plan_type": "hosting", "confidence": 0.82, "flag": false, "pipeline_stage": "refiltered" } }` |
| 200 | Dropped (confidently not plans) | `{ "link": { "refilter_state": "dropped", "confidence": 0.11 } }` |
| 409 | Link has no discoverable HTML summary | error `code: "link_not_ready"` |
| 202 | LLM budget exhausted | error `code: "awaiting_llm_budget"`; verdict not written, link parks and resumes (FR-048) |

The filter is **recall-biased**: a link is dropped only when the model is confidently certain
it is not a plans page; borderline links are kept and flagged (`flag: true`) so providers are
not silently lost (FR-014). The verdict (kept/dropped, plan type, confidence, flag) is
recorded before capture (FR-015). There is no page-capture call in this section — capture is
server-side and lives in section 4.

### POST /api/v1/ops/links/{link_id}/refilter/override

An operator may override a verdict (keep a dropped link or drop a kept one), recorded with the
actor and reason.

**Request**: `{ "refilter_state": "kept", "reason": "pricing table further down the page" }`
→ `200` with the updated link.

## 4. Server-side headless capture (FR-016..FR-019)

Capture runs **headless on the server** through domtrack's capture capability; no operator
machine and no local domtrack installation are involved (FR-016, SC-008). A capture navigates
the link, waits for the page to settle, scrolls to trigger lazily loaded content, and records
for a **configured fixed duration** — headless capture requires a fixed duration (FR-017).

### POST /api/v1/ops/links/{link_id}/captures

Start a headless capture for a kept link.

**Request**: `{ "duration_ms": 60000 }` (optional; falls back to the configured default)

**Responses**

| Status | Meaning | Body |
|--------|---------|------|
| 201 | Capture session started | `{ "capture_session": { "id", "state": "recording", "mode": "headless_fixed", "duration_ms": 60000 } }` |
| 400 | Link is not `kept`/refiltered | error `code: "link_not_ready"` |
| 409 | A capture is already in flight for this link | error `code: "capture_in_progress"` |
| 502 | Capture failed after retries | error `code: "dead_lettered"`; the link does not advance (FR-018, FR-052) |

Per-link work runs as Django Tasks (`django.tasks`); no Celery broker is involved. A link is
captured only on this explicit call (or by the scheduled/rerun pipeline); discovering or
refiltering a link never records it.

### GET /api/v1/ops/links/{link_id}/captures

List the link's capture sessions with state, mode, duration, and the stored trace reference,
so the UI can show progress (`recording` → `stored` / `failed`).

### POST /api/v1/ops/captures/{capture_session_id}/trace

Store the trace domtrack produced for the capture. The server produced the trace, so this is
a server-side hand-off, not an operator upload.

**Responses**

| Status | Meaning | Body |
|--------|---------|------|
| 201 | Trace stored | `{ "trace": { "id", "link_id", "captured_at", "byte_size", "content_sha256", "is_valid_trace": true, "storage_key": "traces/9f1c….json" }, "link": { "pipeline_stage": "captured" } }` |
| 400 | Artifact is not a domtrack trace | error `code: "invalid_field"` (Pydantic boundary check) |
| 404 | Unknown capture session | error `code: "not_found"` |

The trace is stored **unmodified** as a domtrack trace file (FR-000a, FR-019) in the
`STORAGES`-configured artifact store (S3-compatible by default) under a **UUID-based object
key**; the database keeps only the key, backend alias, size, and hash — never the trace body.
A link does not advance to extraction until a valid trace is stored; artifact storage and
database writes are ordered and compensated so the two never diverge (FR-018, FR-053,
SC-009).

### POST /api/v1/ops/captures/{capture_session_id}/fail

Record a failed capture (navigation timeout, domtrack crash, retries exhausted) so the attempt
is auditable and the link is dead-lettered if retries are exhausted (FR-018, FR-052).

**Request**: `{ "error": "navigation_timeout" }` → `200` with `state: "failed"`.

## 5. Table extraction (FR-020..FR-022)

Extraction calls domtrack's table-discovery capability on the link's stored trace and persists
the returned tables. Every page is processed **independently**, with no cross-page alignment
(FR-020, SC-010).

### POST /api/v1/ops/links/{link_id}/extractions

**Responses**

| Status | Meaning | Body |
|--------|---------|------|
| 201 | Tables extracted | `{ "extraction": { "trace_id", "table_count", "tables": [ { "id", "parent", "column_count", "row_count" } ] }, "link": { "pipeline_stage": "extracted" } }` |
| 409 | No stored trace | error `code: "trace_required"` (FR-018) |
| 200 | domtrack returned no tables | `{ "table_count": 0, "link": { "pipeline_stage": "flagged" } }` (FR-022) |

Extraction is deterministic: re-running it on the same trace replaces the previous extraction
and yields identical tables (FR-021, SC-010). It runs as a Django Task for large traces; the
endpoint returns the task's result synchronously in development (immediate backend).

### GET /api/v1/ops/links/{link_id}/tables

List the link's extracted tables with their columns (id, path/selector as domtrack reports it,
`atype`, `coverage`) and rows, plus the current classification verdict per table. Columns and
rows are shown for review only; they are **not** mapping inputs.

## 6. Table classification (FR-023..FR-025)

Every extracted table is classified by an LLM as a plans table or not, with the matched plan
type and a **confidence** (probability of the verdict). Classification is per table and per
page: a page may hold zero, one, or several plans-table verdicts (FR-023, FR-024, SC-011).

### POST /api/v1/ops/links/{link_id}/classifications

Classify the link's extracted tables.

**Responses**

| Status | Meaning | Body |
|--------|---------|------|
| 200 | Classified | `{ "classifications": [ { "table_id", "is_plans_table", "plan_type", "confidence" } ], "link": { "pipeline_stage": "classified" } }` |
| 409 | No tables to classify | error `code: "no_tables_found"` (FR-022) |
| 202 | LLM budget exhausted | error `code: "awaiting_llm_budget"`; no classification written, the link parks and resumes (FR-048) |

The persisted classification is the **anchor** by which replay decides whether a detected
change is relevant to plan data (FR-025).

### GET /api/v1/ops/links/{link_id}/classifications

List the per-table verdicts (plans/not-plans, plan type, confidence) for the link.

## 7. Plan schema extraction (FR-026..FR-031)

For each table classified as a plans table, the system extracts the plans as **data** with an
LLM against the single plan schema and returns a list of plan records in the standard format
(FR-026). The LLM produces the data values itself, including normalizing amounts, units, and
billing periods; **no selectors, no formulas, and no recipe are produced or stored** (FR-028,
SC-012).

### GET /api/v1/ops/plan-schema?plan_type=hosting

Return the code-defined plan schema (fields, types, required flags, units, enums) for a plan
type (FR-027). The schema is read-only; it is edited by hand in code and is not user-editable.

### POST /api/v1/ops/links/{link_id}/plans

Extract plan data for the link's classified plans tables.

**Request (optional)**: `{ "classification_ids": [55] }` (default: all plans-table
classifications for the link)

**Responses**

| Status | Meaning | Body |
|--------|---------|------|
| 201 | Plan data extracted | `{ "plans": [ { "id", "classification_id", "plan_type", "fields": { ... } } ], "link": { "pipeline_stage": "plans_extracted" } }` |
| 409 | No plans-table classification | error `code: "plans_required"` |
| 202 | LLM budget exhausted | error `code: "awaiting_llm_budget"`; no plan row written, the link parks and resumes (FR-048) |

When a plans table cannot be mapped to the schema, **that table is skipped** and mappable
tables on the same page are still extracted; a record never contains an unpopulated required
field (FR-030, SC-013). Re-extraction is idempotent for an unchanged table: the same table
yields the same plan records (FR-031). Extraction always re-runs the LLM against the plan
data; no formula or selector replay is performed (FR-029).

### GET /api/v1/ops/links/{link_id}/plans

List the link's extracted plan records with their provenance (`classification_id`, `trace_id`)
and current publish state.

## 8. Optional LLM labeling (FR-032..FR-035)

### POST /api/v1/ops/links/{link_id}/labeling

Run domtrack's table labeling on the link's extracted tables (server-side), gated by the admin
toggle.

**Responses**

| Status | Meaning | Body |
|--------|---------|------|
| 200 | Labels applied | `{ "labeled_tables": 3, "labels": [ { "table_id", "column_id", "label" } ], "tokens_used": 1840 }` |
| 403 | Labeling disabled | error `code: "labeling_disabled"` (default; FR-032) |
| 202 | LLM budget exhausted | error `code: "awaiting_llm_budget"`; no labels written, work parks and resumes (FR-035, FR-048) |

Labels are additive: a link with labels and a link without behave identically in extraction,
classification, plan extraction, publishing, and replay (FR-034, SC-019).

## 9. Publishing and provenance (FR-036..FR-038)

### POST /api/v1/ops/links/{link_id}/publish

Publish the link's extracted plan records to the main site with provenance.

**Responses**

| Status | Meaning | Body |
|--------|---------|------|
| 200 | Published | `{ "published": 24, "link": { "pipeline_stage": "published" } }` |
| 409 | No plan data to publish | error `code: "plans_required"` (FR-026, FR-036) |

Published plan records are **owned by the `catalog` app**; the console writes them through
`catalog/interfaces.py` (`upsert_published_record`), never by touching `catalog`'s tables
(Principle V). Each `PublishedRecord` carries its site, link, trace, and the plans-table
`classification` that made it eligible (FR-037). A replay that reports an item removed calls
`retire_published_record` through the same interface instead of retaining stale values
(FR-038). There is no cleaning stage: plan records are already normalized by the LLM at
extraction time (FR-028).

## 10. Scheduled replay, change detection, and alerting (FR-039..FR-046)

### GET /api/v1/ops/replay-runs?link_id=&state=

List replay runs with their before/after traces, the change classification (content
/structural), whether re-extraction ran (`reextracted`), the applied flag, the run state, and
domtrack replay stats (FR-039, FR-041).

### POST /api/v1/ops/replay-runs

Run a replay cycle on demand (the same code path the `run_scheduled_replays` command drives).

**Request**: `{ "link_ids": [901], "site_id": 7 }` (or neither to run all due links)

**Response 202**: `{ "enqueued": 12, "due_after": "2026-10-31T18:00:00Z" }`

Per-link work runs as Django Tasks (`django.tasks`); no Celery broker is involved. Each run
performs domtrack's **compare** capability in one call — replay, record-during-replay, and
diff — against the previous trace (FR-040). Each detected change is classified as a
**content change** or a **structural change** (FR-041). When a change touches a region
classified as a plans table, the run re-runs the LLM schema extraction against the schema and
refreshes the published plan data; when the change is **structural**, the run first re-runs
table discovery and re-classifies the plans table on the fresh trace, then re-extracts
(FR-042). Content and structural changes that touch a plans table both trigger LLM
re-extraction; a change that does **not** touch a plans table triggers no LLM work (FR-043).

When the token budget is exhausted mid-run, the run parks in `awaiting_llm_budget`; non-LLM
stages continue and the run resumes when budget is restored (FR-048).

### GET /api/v1/ops/links/{link_id}/failure

Return the link's failure rate, the trailing window used, the configured threshold, and the
current alert state (FR-044).

### GET /api/v1/ops/alerts?state=open

List failure alerts. An alert names the link that needs updating (FR-044, SC-017).

### POST /api/v1/ops/links/{link_id}/rerun

Re-run the maintenance stages (discover, refilter, capture, extract, classify, extract-schema,
publish) for a flagged link (FR-046, SC-017). Returns the link's current `pipeline_stage`.

### GET | POST | DELETE /api/v1/ops/notification-recipients

Manage the alert recipient list (FR-045). Recipients and notifications are owned by the
general-purpose **`notifications` app**; this path is a thin console facade over
`notifications/interfaces.py` (or the notifications app's own admin endpoints), so other
features reuse the same recipients and delivery machinery. `DELETE` deactivates rather than
erases (`is_active=false`) so delivered-notification history is preserved. Alerts raised by
replay, and the budget-exhaustion notice, are delivered on the **in-app** channel (email is
out of scope by project decision).

**POST request**: `{ "user_id": 42, "name": "Ops" }` → `201`.
A duplicate active user returns `409`/`410` per the notifications contract.

## 11. Console settings and observability (FR-047, FR-054..FR-057)

### GET | PUT /api/v1/ops/settings

Read and update the runtime tunables surfaced to operators (django-constance, database
backend): the adaptive-crawl seed/query and page/depth bounds, the denied file extensions and
path segments, the refilter provider/model/confidence drop threshold, capture duration and
navigation timeout, the replay period, the failure-rate threshold and window, the labeling
toggle/provider/model/language/batch size, and the retry/backoff/dead-letter thresholds
(FR-054, SC-018).

### GET | PUT /api/v1/ops/llm-token-budget

Read and set the LLM **token budget** per period (Principle II, FR-047). Setting the budget
requires the admin role. The budget gates every LLM stage — refilter, classification, plan
schema extraction, and labeling; when it is exhausted, non-LLM stages continue, LLM-gated work
parks in `awaiting_llm_budget`, and the admin is notified (FR-048, FR-049). Spend is attributed
per link and per table, and each logical call carries an idempotency key so a retry is not
charged twice (FR-049, FR-050).

### GET /api/v1/ops/metrics

Operations metrics: crawl success rate per provider/company, per-source latency, LLM token
usage and cumulative spend, replay staleness, and open alert count (FR-049, FR-055, FR-056,
Principle VII). All results are masked of personal data (FR-055, SC-021).
