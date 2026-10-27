# Contract: Operator Console API (v1)

Base path: `/api/v1/ops`. The console lives at `/ops` in the frontend (deliberately not
`/admin`, which is Django's built-in admin site) and this is its API prefix. Everything the
operator console does — the approval queue,
site onboarding, link review, capture, extraction, labeling, mapping, cleaning, publishing,
replay, and alerts — is served from this prefix. This contract is the reviewed source of
intent; the generated OpenAPI schema (drf-spectacular) is the machine-readable form.

Two concerns are **not** owned by this module and appear here only as the call the console
makes on the caller's behalf: published plan records are written by the `catalog` app through
its interface, and notifications are delivered by the `notifications` app through its
interface (see sections 7 and 8).

Company **verification** is recorded by delegating to `companies` (see the feature-002
contract for the canonical decision semantics). The `admin_console` decision endpoint is a
thin console facade over `CompaniesInterface.record_verification_decision`; there is still
exactly one append-only `VerificationDecision` record per decision (FR-002, FR-006, SC-001).

## Conventions

- Authentication: `Authorization: Bearer <access_token>` on every endpoint here (JSON Web
  Token auth from the `accounts` feature, Principle XI). Unauthenticated requests get `401`.
- Authorization: every endpoint requires the operator/admin role (`is_admin()`); a
  non-operator caller gets `403` with `code: "admin_required"` (FR-001, FR-005). A company
  owner can never reach a decision or maintenance endpoint (FR-005, SC-004).
- CSRF: state-changing requests MUST include `X-CSRFToken` matching the CSRF cookie.
- Masking: no response or log includes a full company phone number, and no response or log
  includes trace content (FR-044, SC-018).
- Idempotency: `GET` endpoints are side-effect free; capture start, extraction, replay, and
  notification dispatch are explicitly guarded against duplicate execution (documented per
  endpoint).

### Error shape

```json
{
  "error": {
    "code": "recipe_incomplete",
    "message": "This link cannot be mapped while required schema fields are unconnected.",
    "fields": { "unconnected": ["storage_amount", "price_amount"] }
  }
}
```

Error codes used by this contract: `admin_required`, `not_authenticated`, `not_found`,
`invalid_field`, `domtrack_unreachable`, `link_not_ready`, `trace_required`,
`no_tables_found`, `recipe_incomplete`, `labeling_disabled`, `llm_ceiling_exceeded`,
`site_suspended`, `alerts_configured_recipient_exists`.

## 1. Approval queue (FR-001, FR-004)

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
      "phone_masked": "021****789",
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
`onboarding` and the maintenance lifecycle started (FR-003). `not_approved` ⇒ company stays
unverified, step one reopens, and its `Site` is suspended (FR-003, edge case).

## 2. Site onboarding and link review (FR-007..FR-011)

### POST /api/v1/ops/sites

Onboard the company's single site.

**Request**: `{ "company_id": 42 }`

**Responses**

| Status | Meaning | Body |
|--------|---------|------|
| 201 | Site onboarded | `{ "site": { "id", "domain", "has_sitemap", "sitemap_url", "maintenance_state": "onboarding" } }` |
| 409 | Company already has a site | error `code: "invalid_field"`, `fields: {"company_id": "already onboarded"}` (FR-007) |
| 403 | Company is not approved/verified | error `code: "link_not_ready"` |

### POST /api/v1/ops/sites/{site_id}/discover-links

Enumerate candidate links from the site's sitemap (robots.txt `Sitemap:` directives, then
`/sitemap.xml`, following sitemap indexes) and store them as `candidate` links.

**Response 200**

```json
{
  "site": { "id": 7, "has_sitemap": true, "sitemap_url": "https://example.com/sitemap.xml" },
  "discovered": 128,
  "candidates": [ { "id": 901, "url": "https://example.com/hosting/basic", "source": "sitemap" } ]
}
```

When no sitemap is discoverable, `has_sitemap=false` and `discovered=0`; the operator then
enters links manually (FR-008). Discovery is idempotent on `(site, url_hash)`.
Fetching honors robots.txt, uses the transparent user-agent, and rate-limits per domain
(Principle X).

### POST /api/v1/ops/sites/{site_id}/links

Enter links manually (for sites without a usable sitemap).

**Request**: `{ "urls": ["https://example.com/hosting/pro", "https://example.com/vps"] }`

**Response 201**: the created `candidate` links with `source: "manual"` (FR-008).

### GET /api/v1/ops/sites/{site_id}/links?review_state=candidate

List links for operator review.

### POST /api/v1/ops/sites/{site_id}/links/review

Submit the review: keep some links and remove the rest (FR-009, FR-010).

**Request**

```json
{ "keep": [901, 902], "remove": [903, 904] }
```

**Response 200**

```json
{
  "kept": 2,
  "removed": 2,
  "site": { "maintenance_state": "active" }
}
```

Removed links transition to `review_state="removed"` and are excluded from capture while
remaining recorded (FR-010, SC-006). A review that keeps no links leaves the site in
`onboarding` and returns `code: "link_not_ready"` with an explanatory message (FR-011).

## 3. Operator-driven capture (FR-012..FR-017)

### POST /api/v1/ops/links/{link_id}/captures

Start a capture for a kept link. The server calls the operator's **local domtrack REST API**
(`POST {DOMTRACK_LOCAL_API_URL}/capture`), which opens a Chrome window on the link and
starts recording.

**Request**: `{ "mode": "interactive" }` (or `{ "mode": "fixed_duration", "duration_ms": 60000 }`,
FR-013)

**Responses**

| Status | Meaning | Body |
|--------|---------|------|
| 201 | Capture session started | `{ "capture_session": { "id", "state": "recording", "mode": "interactive" } }` |
| 400 | Link is not `kept`/ready | error `code: "link_not_ready"` |
| 502 | Local domtrack unreachable | error `code: "domtrack_unreachable"`; the link does **not** advance (FR-017) |

### POST /api/v1/ops/captures/{capture_session_id}/trace

Deliver the trace domtrack produced. The console attempts automatic transfer first; when the
browser cannot read the local file, the same endpoint accepts an operator-confirmed manual
upload (FR-015).

**Request**: `multipart/form-data` with the trace file, or JSON
`{ "local_path": "/home/op/.domtrack/traces/abc.json" }` for a helper-read path.

**Responses**

| Status | Meaning | Body |
|--------|---------|------|
| 201 | Trace stored | `{ "trace": { "id", "link_id", "captured_at", "byte_size", "content_sha256", "is_valid_trace": true, "storage_key": "traces/9f1c….json" }, "link": { "pipeline_stage": "capture" } }` |
| 400 | Body is not a domtrack trace | error `code: "invalid_field"` (Pydantic boundary check) |
| 404 | Unknown capture session | error `code: "not_found"` |

The trace is stored **unmodified** as a domtrack trace file (FR-000a, FR-016) in the
`STORAGES`-configured artifact store (S3-compatible by default) under a **UUID-based object
key**; the database keeps only the key, backend alias, size, and hash — never the trace body.
The link does not advance to extraction until it is stored (FR-014, SC-007).

### POST /api/v1/ops/captures/{capture_session_id}/fail

Record a failed/cancelled capture (operator cancelled, domtrack crashed) so the attempt is
auditable and the link stays at `capture` (edge case, FR-017).

**Request**: `{ "error": "operator_cancelled" }` → `200` with `state: "failed"`.

## 4. Table extraction (FR-018..FR-020)

### POST /api/v1/ops/links/{link_id}/extractions

Run domtrack's table discovery on the link's stored trace and persist the returned tables.

**Responses**

| Status | Meaning | Body |
|--------|---------|------|
| 201 | Tables extracted | `{ "extraction": { "trace_id", "table_count", "tables": [ { "id", "parent", "score", "column_count", "row_count" } ] }, "link": { "pipeline_stage": "extracted" } }` |
| 409 | No stored trace | error `code: "trace_required"` (FR-014) |
| 200 | domtrack returned no tables | `{ "table_count": 0, "link": { "pipeline_stage": "flagged" } }` (FR-020) |

Re-running extraction on the same trace replaces the previous extraction and yields
identical rows (FR-019, SC-008). Extraction runs as a Django Task for large traces; the
endpoint returns the task's result synchronously in development (immediate backend).

### GET /api/v1/ops/links/{link_id}/tables

List the link's extracted tables with their columns (id, label, **path/selector**,
`atype`, `coverage`) and rows for the mapping workspace (FR-025).

## 5. Optional LLM labeling (FR-021..FR-024)

### POST /api/v1/ops/links/{link_id}/labeling

Run domtrack's table labeling on the link's extracted tables (server-side), gated by the
admin toggle.

**Responses**

| Status | Meaning | Body |
|--------|---------|------|
| 200 | Labels applied | `{ "labeled_tables": 3, "labels": [ { "table_id", "column_id", "label" } ], "llm_cost": "0.0041" }` |
| 403 | Labeling disabled | error `code: "labeling_disabled"` (default; FR-021) |
| 409 | Ceiling would be exceeded | error `code: "llm_ceiling_exceeded"`; no labels written, situation reported (FR-024) |

Labels are additive: a link with labels and a link without behave identically in extraction,
mapping, cleaning, publishing, and replay (FR-023, SC-016).

## 6. Merge and mapping (FR-025..FR-031)

### GET /api/v1/ops/plan-schema?plan_type=hosting

Return the code-defined plan schema (fields, types, required flags, units, enums) for a plan
type (FR-027). The schema is read-only.

### GET /api/v1/ops/links/{link_id}/recipe

Return the current extraction recipe: selected `plan_type` and, per bound field, the source
table, source column, selector (`path`), formula, and aggregation (FR-031).

### PUT /api/v1/ops/links/{link_id}/recipe

Save the mapping produced in the Handsontable workspace.

**Request**

```json
{
  "plan_type": "hosting",
  "bindings": [
    { "schema_field_key": "storage_amount", "source_table": 12, "source_column": "c3",
      "formula": "=VALUE(LEFT(C2,LEN(C2)-2)) * IF(RIGHT(C2,2)=\"TB\",1024,1)", "aggregation": "row" },
    { "schema_field_key": "price_amount", "source_table": 12, "source_column": "c7",
      "formula": "=ROUND(VALUE(SUBSTITUTE(G2,\",\",\"\")),0) * 10", "aggregation": "row" }
  ]
}
```

Formulas are **Excel/spreadsheet-valid** expressions (column/cell references, spreadsheet
operators, and a whitelisted function set such as `SUM`, `MIN`, `MAX`, `IF`, `ROUND`,
`VALUE`, `SUBSTITUTE`, `CONCATENATE`/`&`, `,` argument separator), validated at the boundary;
no arbitrary code is executed (FR-028).

**Responses**

| Status | Meaning | Body |
|--------|---------|------|
| 200 | Recipe saved (new version) | `{ "recipe": { "version", "plan_type", "is_complete", "unconnected": [] }, "link": { "pipeline_stage": "mapped" } }` |
| 400 | Invalid formula or unknown field/column | error `code: "invalid_field"` |
| 409 | Required schema field unconnected | error `code: "recipe_incomplete"`; the link is **not** marked mapped and cannot be published (FR-030, SC-009) |

Reopening the workspace (`GET .../recipe`) restores previously saved selectors and formulas
(FR-031); every replay evaluates this recipe, so no re-mapping is required (FR-029, SC-010).

## 7. Cleaning and publishing (FR-032..FR-036)

### POST /api/v1/ops/links/{link_id}/cleaning

Clean and standardize the mapped data so filters can be applied.

**Response 200**

```json
{
  "cleaned_records": 24,
  "exceptions": [ { "row_index": 7, "field": "bandwidth_amount", "value": "unlimited" } ],
  "link": { "pipeline_stage": "cleaned" }
}
```

Cleaning is automatic by default; only unresolvable exceptions are returned to the operator,
and the rest of a record with exceptions stays cleaned and publishable (FR-033).

### POST /api/v1/ops/links/{link_id}/publish

Publish cleaned data to the main site with provenance.

**Responses**

| Status | Meaning | Body |
|--------|---------|------|
| 200 | Published | `{ "published": 24, "link": { "pipeline_stage": "published" } }` |
| 409 | Recipe incomplete or nothing cleaned | error `code: "recipe_incomplete"` (FR-030, FR-034) |

Published plan records are **owned by the `catalog` app**; the console writes them through
`catalog/interfaces.py` (`upsert_published_record`), never by touching `catalog`'s tables
(Principle V). Each `PublishedRecord` carries site, link, trace, and recipe references
(FR-035). A replay that reports an item removed calls `retire_published_record` through the
same interface instead of retaining stale values (FR-036).

## 8. Scheduled replay and failure alerting (FR-037..FR-042)

### GET /api/v1/ops/replay-runs?link_id=&state=

List replay runs with their before/after traces, diff summary, applied flag, and domtrack
replay stats (FR-037, FR-038).

### POST /api/v1/ops/replay-runs

Run a replay cycle on demand (the same code path the `run_scheduled_replays` command drives).

**Request**: `{ "link_ids": [901], "site_id": 7 }` (or neither to run all due links)

**Response 202**: `{ "enqueued": 12, "due_after": "2026-10-27T18:00:00Z" }`

Per-link work runs as Django Tasks (`django.tasks`); no Celery broker is involved. Each run
launches domtrack's replay + record-during-replay, then domtrack's compare/diff, applies the
diff, and records the failure count (FR-038, FR-039).

### GET /api/v1/ops/links/{link_id}/failure

Return the link's failure rate, the trailing window used, the configured threshold, and the
current alert state (FR-040).

### GET /api/v1/ops/alerts?state=open

List failure alerts. An alert names the link that needs updating (FR-040, SC-013).

### POST /api/v1/ops/links/{link_id}/rerun

Re-run the maintenance stages (capture → extract → map → clean → publish) for a flagged link
(FR-042, SC-014). Returns the link's current `pipeline_stage`.

### GET | POST | DELETE /api/v1/ops/notification-recipients

Manage the alert recipient list (FR-041). Recipients and notifications are owned by the
general-purpose **`notifications` app**; this path is a thin console facade over
`notifications/interfaces.py` (or the notifications app's own admin endpoints), so other
features reuse the same recipients and delivery machinery. `DELETE` deactivates rather than
erases (`is_active=false`) so delivered-notification history is preserved. Alerts raised by
replay are delivered on **both** the in-app and email channels.

**POST request**: `{ "email": "ops@example.com", "name": "Ops" }` → `201`.
A duplicate active email returns `409` `code: "alerts_configured_recipient_exists"`.

## 9. Console settings and observability (FR-043..FR-045)

### GET | PUT /api/v1/ops/settings

Read and update the runtime tunables surfaced to operators (django-constance, database
backend): replay period, failure-rate threshold and window, labeling toggle/provider/model/
language/batch size, sitemap fetch timeout and index depth, link discovery cap, and cleaning
rules (FR-043, SC-015). The LLM **cost ceiling** is managed through the model-backed cost
endpoint below, not here (Principle II).

### GET | PUT /api/v1/ops/llm-cost-ceiling

Read and set the LLM cost ceiling per scope and period (Principle II, FR-024). Setting a
ceiling requires the admin role.

### GET /api/v1/ops/metrics

Operations metrics: crawl success rate per provider/company, per-source latency, LLM call
count and cumulative cost, replay staleness, and open alert count (FR-045, Principle VII).
