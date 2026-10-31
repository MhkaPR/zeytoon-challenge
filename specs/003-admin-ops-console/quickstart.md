# Quickstart Validation: Admin Console — Company Approval & Automated Site Data Pipeline

A runnable guide to prove the feature works end-to-end. It references
[spec.md](./spec.md), [data-model.md](./data-model.md),
[contracts/ops-console-api.md](./contracts/ops-console-api.md), and
[contracts/domtrack-integration.md](./contracts/domtrack-integration.md) instead of
duplicating their details.

## Prerequisites

- Python 3.14 with the project virtualenv active; backend dependencies installed
  (including `domtrack` and its `playwright` extra).
- PostgreSQL (or the local SQLite default) and Redis reachable.
- An operator account in the `admin` group, and a logged-in JWT for it.
- A company that has completed registration and is awaiting verification (from the
  company-registration feature).
- For discovery/capture scenarios only: a server with a headless Chromium available to both
  `crawl4ai` and `domtrack` (no operator-machine service is used).
- For the LLM stages (refilter, classification, plan extraction, labeling): an
  OpenAI-compatible gateway base URL + API key in the environment, and an admin-set token
  budget.

### Create the operator account

The console is role-gated. Membership in the `ops` group grants the console only;
`admin` (or a superuser) is a superset that also grants Django `/admin`. A regular user is
redirected to `/panel`. Create an operator from the backend shell, then log in with the same
phone number through the normal SMS OTP dialog:

```bash
python manage.py shell -c "
from django.contrib.auth.models import Group
from accounts.models import User, ensure_role_groups
ensure_role_groups()
user, _ = User.objects.get_or_create(phone_number='+989123456789', defaults={'username': '+989123456789'})
user.groups.add(Group.objects.get(name='ops'))
user.save()
print(user.phone_number, user.role())
"
```

Use the `admin` group (plus `is_staff=True`) when the same person must also open
`/admin`. `python manage.py createsuperuser --phone_number ...` is the fastest way to make
an admin.

After signing in, the header user menu shows an **ops console** item for `ops`/`admin`.
Opening
`/ops` directly is supported: when signed out it shows the operator notice plus a login
button, and after login the app returns you to `/ops` (the path is in
`RETURN_URL_ALLOWLIST`). A signed-in non-operator is redirected to `/panel`.

## Setup

```bash
# from repo root
cd backend/src
python manage.py startapp admin_console        # if the scaffold is not present yet
python manage.py startapp notifications        # general-purpose notifications app
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Register `admin_console` in `INSTALLED_APPS`, mount `/api/v1/ops/` in `config/urls.py`,
and add the constance constants and the `TASKS` setting described in
[research.md](./research.md) (R2, R16) and [data-model.md](./data-model.md). Set
the LLM gateway `OPENAI_BASE_URL` / `OPENAI_API_KEY` in the environment, register the new
`notifications` app, and configure artifact storage through Django's `STORAGES` setting
(S3-compatible by default via `django-storages`; set it to local filesystem for a developer
machine). Server-side headless capture needs a headless Chromium available to the worker; no
operator machine and no `DOMTRACK_LOCAL_API_URL` are involved. No Celery broker and no Celery
worker are involved; scheduled work is driven by `python manage.py run_scheduled_replays`.

```bash
# in a second terminal
cd frontend
yarn install
yarn dev                # open http://localhost:3000/ops
```

Use the local SQLite/Redis defaults. The admin area is role-gated; log in with the operator
account before opening `/ops`.

## Operator Console README

### `/ops` vs Django `/admin`

- `/ops` is the operator console built in this feature (Next.js, Persian/RTL). It is the
  only place operators approve companies and run the site-maintenance pipeline. Every API
  call goes to `/api/v1/ops/` and requires the `ops` or `admin` role; a signed-in
  non-operator is redirected back to `/panel`.
- `/admin` remains Django's built-in admin site for low-level reads of the registered
  models (sites, links, captures, traces, tables, classifications, plans, replay runs, alerts, LLM ledger,
  notifications and recipients). Do not treat `/admin` as the operator workflow.

### Server-side capture, crawl4ai, and the LLM gateway

Link discovery, capture, replay/compare, diff, HTML rebuild, table extraction, and labeling
are all served on the server by `crawl4ai` and `domtrack`; the console never reimplements
them. No operator-machine service is used — capture is headless on the server and requires a
headless Chromium on that host:

```bash
# server host: headless Chromium for domtrack + crawl4ai
python -m playwright install chromium

# LLM gateway for refilter / classification / plan extraction / labeling
export LLM_BASE_URL=https://<your-openai-compatible-gateway>/v1
export LLM_API_KEY=...
```

The admin sets the **LLM token budget** in the console settings; when it is exhausted, the
non-LLM stages continue and LLM-gated links wait in `awaiting_llm_budget` until the budget is
restored. Stored artifacts are domtrack's native trace files.

### Artifact storage switch (`STORAGES`)

The default `STORAGES["default"]` is S3-compatible through `django-storages`. Configure it
with `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_ENDPOINT_URL`, `AWS_S3_REGION_NAME`,
`AWS_ACCESS_KEY_ID`, and `AWS_SECRET_ACCESS_KEY`. Only the artifact body lives in the store;
the database keeps the UUID-based `storage_key`.

For a developer machine without S3, switch `STORAGES["default"]` to Django's filesystem
backend in `backend/src/config/settings.py` (the commented local alternative) and set a
local `MEDIA_ROOT`. No pipeline code changes are needed: artifact reads/writes go through
`admin_console/artifacts.py`.

### Notifications

Alerts are delivered **in-app only** by project decision. Recipients are admin-managed at
`/api/v1/ops/notification-recipients`, and each alert writes one in-app delivery per active
recipient. There is no email channel or SMTP configuration.

## Validation Scenarios

### V1 — Company approval queue and decision — proves FR-001..FR-006, SC-001..SC-004

1. As the operator, open `/ops` (or `GET /api/v1/ops/approvals`).
2. **Expected**: the pending company appears with name, representative, domain, masked phone,
   and a duplicate-domain warning when its normalized domain matches another company.
3. `POST /api/v1/ops/companies/{id}/verification-decisions` with `{"outcome":"approved"}`.
4. **Expected**: `201`; the company is verified, its panel becomes reachable, exactly one
   append-only decision record exists (outcome, operator, time, note), and a `Site` in
   `onboarding` now exists for it.
5. On another pending company record `{"outcome":"not_approved"}`.
6. **Expected**: the company stays unverified, registration step one reopens, one decision
   record exists, and any existing `Site` is `suspended`.
7. Attempt the same decision as the company owner (owner JWT).
8. **Expected**: `403 admin_required`; the company's status is unchanged (SC-004).

### V2 — Automated link discovery — proves FR-007..FR-011, SC-005..SC-006

1. `POST /api/v1/ops/sites` with the approved company's id.
2. **Expected**: `201` with `maintenance_state="onboarding"`, the company's domain, and no
   sitemap fields. Onboarding the same company again returns `409` (one site per company).
3. `POST /api/v1/ops/sites/{id}/discover-links`.
4. **Expected**: the system runs crawl4ai's adaptive crawler with the **statistical strategy**
   (keyword/BM25 only — no embeddings, no LLM) from the site domain and the configured
   host/server-plans query; no sitemap is fetched, parsed, or required. The harvest is
   reduced by the deterministic policy (same-host, fragments/query strings stripped, denied
   extensions and path segments removed, deduplicated) and stored as `source="adaptive_crawl"`
   candidates (SC-005, SC-006).
5. **Expected**: the response reports both `discovered` (raw harvest) and `after_policy`
   (survivors). Edge case: when the crawl yields no candidates, `discovered=0`, the site stays
   in `onboarding`, the operator is informed (FR-011), and a crawl failure returns
   `502 crawl_failed` without changing the site.
6. Optional manual entry: `POST /api/v1/ops/sites/{id}/links` with two URLs.
7. **Expected**: `201` with `source="manual"` candidates (edge case only).

### V3 — LLM link refilter — proves FR-012..FR-015, SC-007

1. `POST /api/v1/ops/links/{id}/refilter` for a candidate link.
2. **Expected**: the model receives only the URL, the `h1–h3` headings, and the important
   section (largest text-density block in `<main>`/`<article>`) — never the page HTML — and
   the link stores `refilter_plan_type`, `refilter_confidence`, and `refilter_flag`.
3. Refilter a confidently non-plans page.
4. **Expected**: the link becomes `dropped` and is recorded as not-a-plans-page.
5. Refilter a borderline page.
6. **Expected**: the link is kept and `refilter_flag=true`.
7. Exhaust the token budget and refilter another link.
8. **Expected**: the link waits in `awaiting_llm_budget` (no error) and the rest of the
   pipeline continues.

### V4 — Server-side headless capture — proves FR-016..FR-019, SC-008..SC-009

1. `POST /api/v1/ops/links/{id}/captures` for a kept link.
2. **Expected**: the **server** opens the link headlessly, waits for the page to settle,
   scrolls to trigger lazy content, records for the configured fixed duration, and stores a
   `Trace` with `is_valid_trace=true` and a UUID-based `storage_key`; no operator or browser
   window is involved (SC-008).
3. Attempt extraction on a link with no stored trace.
4. **Expected**: `409 trace_required` (no advance without a trace, FR-018).
5. Simulate a navigation failure / browser crash.
6. **Expected**: the session becomes `failed`, the link does not advance, and the failure is
   recorded (SC-009).

### V5 — Table extraction — proves FR-020..FR-022, SC-010

1. `POST /api/v1/ops/links/{id}/extractions` for a link with a stored trace.
2. **Expected**: `201` with one or more tables stored as `ExtractedTable` records linked to
   the link and trace, each column carrying domtrack's `path` and `coverage`.
3. Repeat the same call.
4. **Expected**: identical rows (same trace ⇒ same tables, SC-010). Extraction is per page,
   with no cross-page alignment.
5. Run extraction on a trace with no tabular structure.
6. **Expected**: `200` with `table_count=0`; no table rows are stored.

### V6 — Table classification and plan extraction — proves FR-023..FR-031, SC-011..SC-013

1. `POST /api/v1/ops/links/{id}/classifications`.
2. **Expected**: each table gets a `TableClassification` with `is_plans_table`, `plan_type`,
   and `confidence`; a page with three tables where one is a plans table yields exactly one
   `is_plans_table=true` verdict.
3. `POST /api/v1/ops/links/{id}/plans`.
4. **Expected**: each plans table yields normalized `PlanRecord`s in the standard schema
   format; the payload contains **no selector and no formula** anywhere (SC-012).
5. Include a table that cannot fill the schema's required fields.
6. **Expected**: that table is skipped and the page's other mappable tables are still
   extracted (SC-013).
7. Re-run plan extraction for an unchanged table.
8. **Expected**: identical records (idempotent, FR-031).

### V7 — Optional labeling — proves FR-032..FR-035, SC-019

1. With labeling at its default (disabled), `POST /api/v1/ops/links/{id}/labeling`.
2. **Expected**: `403 labeling_disabled`; no `SemanticLabel` rows exist, and classification,
   plan extraction, publishing, and replay all still work (0 dependency on labels).
3. Enable labeling as an admin (`PUT /api/v1/ops/settings`) with provider/model/language.
4. `POST /api/v1/ops/links/{id}/labeling`.
5. **Expected**: `200` with meaningful table and column labels stored as `SemanticLabel`
   rows and the call's tokens appended to the ledger.
6. Exhaust the token budget and label again.
7. **Expected**: the link waits in `awaiting_llm_budget`; no labels are written and no
   overspend occurs (FR-035).

### V8 — Publishing — proves FR-036..FR-038, SC-013

1. `POST /api/v1/ops/links/{id}/publish`.
2. **Expected**: `200`; `catalog` publishes records with provenance to site, link, trace, and
   the plans-table `classification`, available to the main site through
   `catalog/interfaces.py` (FR-036, FR-037).
3. Remove a plan from the replayed page (or use a fixture whose diff reports a removal).
4. **Expected**: the corresponding published record is retired rather than retaining a stale
   value (FR-038).

### V9 — Scheduled replay, change detection, and failure alerting — proves FR-039..FR-046, SC-014..SC-017

1. Set a short replay period in the console settings, then run
   `python manage.py run_scheduled_replays` (or `POST /api/v1/ops/replay-runs`).
2. **Expected**: due links are replayed with domtrack compare (replay + record + diff); each
   `ReplayRun` records a before trace, a fresh after trace, and changes classified as
   `content` or `structural` (FR-040, FR-041, SC-014).
3. Change a value inside a region classified as a plans table.
4. **Expected**: the run re-extracts the plan data with the LLM (`reextracted=true`) and
   updates published data (FR-042).
5. Change a region that is not a plans table.
6. **Expected**: no LLM extraction runs (`reextracted=false`) (FR-043, SC-015).
7. Force a link's failure rate past the configured threshold (domtrack reports the failures).
8. **Expected**: one open `FailureAlert` names the link and an in-app notification appears
   for each active recipient; the alert is not repeated on every subsequent replay until it
   resolves (FR-044, FR-045, SC-017).
9. Add and remove a notification recipient as an admin.
10. **Expected**: both operations succeed; removed recipients are deactivated without
    rewriting delivered history.
11. `POST /api/v1/ops/links/{id}/rerun` for the flagged link.
12. **Expected**: the maintenance stages re-run and the link returns to active status
    (FR-046, SC-014).

## Cross-cutting checks

### Tuning without code changes — proves FR-054, SC-018

Change the replay period, failure-rate threshold, labeling toggle, crawl query/bounds, deny
list, refilter threshold, capture duration, and LLM token budget through
`GET | PUT /api/v1/ops/settings`; each change takes effect on the next run without a
redeploy. No tunable is hard-coded.

### No reimplementation of domtrack/crawl4ai — proves FR-000, SC-020

Run the backend test suite; `admin_console/tests/test_domtrack_reuse.py` must pass, proving
every `domtrack` import lives in `admin_console/domtrack_client.py`, every `crawl4ai` import
lives in `admin_console/discovery.py`, and that capture, replay, record-during-replay,
compare, diff, HTML rebuild, table extraction, and labeling are all served by domtrack.

### Budget queue and resilience — proves FR-048, FR-051, FR-052, SC-016, SC-017

Exhaust the token budget mid-cycle and confirm non-LLM stages continue while LLM-gated links
park in `awaiting_llm_budget` and resume when the budget is restored. Force a link to fail
repeatedly and confirm it retries with backoff and is dead-lettered rather than retried
indefinitely, without aborting the cycle.

### Masked logs — proves FR-055, SC-021

Exercise approval, discovery, refilter, capture, extraction, classification, plan extraction,
publishing, and replay, then inspect the structured JSON logs: every event is structured, hot
paths are sampled/aggregated rather than logged per item, and no log entry contains a phone
number or trace content.

## Validation Results

The earlier (superseded) operator-driven design — sitemap discovery, local interactive
capture, the recipe/mapping workspace, and the formula-cleaning engine — was implemented and
validated on 2026-10-29. That design is retired by this rewrite: mapping, recipes, formulas,
and cleaning no longer exist, discovery is adaptive crawling, and capture is server-side and
headless. The rewrite is a specification change; the automated pipeline described above is
**not yet implemented or validated**, so no run results are claimed for it.

When it is implemented, the validation command set is expected to be:

```bash
DJANGO_SETTINGS_MODULE=config.settings PYTHONPATH=backend/src \
  .venv/bin/python -m pytest backend/src/admin_console/tests backend/src/notifications/tests -q

cd frontend && npx vitest run tests/ops-*.test.tsx
```

- **Reuse guard**: `admin_console/tests/test_domtrack_reuse.py` must show `domtrack` imported
  only in `domtrack_client.py` and `crawl4ai` only in `discovery.py` (SC-020).
- **Pipeline coverage to add**: discovery + deterministic policy, refilter input shape and
  recall-bias, headless capture state machine, extraction determinism, classification
  confidence, plan-schema extraction with per-table skip, labeling gate, publishing
  provenance, replay content/structural change classification and conditional re-extraction,
  budget-exhaustion parking, and retry/dead-letter resilience.
- **No local domtrack service**: capture, replay, and compare run server-side through the
  domtrack adapter; there is no operator machine and no `DOMTRACK_LOCAL_API_URL` to probe.
