# Quickstart Validation: Admin Console — Company Approval & Site Data Maintenance

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
- For capture scenarios only: `domtrack serve` running locally on the operator's machine
  with Playwright browsers installed, and `DOMTRACK_LOCAL_API_URL` pointing at it. Use a
  port other than 8000 so the local domtrack service does not collide with the Django dev
  server.
- Optional, for labeling only: an LLM provider API key in the environment.

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
`DOMTRACK_LOCAL_API_URL` in the environment, register the new `notifications` app, and
configure artifact storage through Django's `STORAGES` setting (S3-compatible by default via
`django-storages`; set it to local filesystem for a developer machine). No Celery broker and
no Celery worker are involved; scheduled work is driven by `python manage.py
run_scheduled_replays`.

```bash
# in a second terminal
cd frontend
yarn install            # adds handsontable + @handsontable/react-wrapper on first run
yarn dev                # open http://localhost:3000/ops
```

Use the local SQLite/Redis defaults. The admin area is role-gated; log in with the operator
account before opening `/ops`.

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

### V2 — Site onboarding and link review — proves FR-007..FR-011, SC-005..SC-006

1. `POST /api/v1/ops/sites` with the approved company's id.
2. **Expected**: `201` with `maintenance_state="onboarding"` and `has_sitemap` reflecting the
   domain. Onboarding the same company again returns `409` (one site per company).
3. `POST /api/v1/ops/sites/{id}/discover-links`.
4. **Expected**: when a sitemap exists, candidate links are stored (`source="sitemap"`);
   when none exists, `has_sitemap=false` and `discovered=0`.
5. For the no-sitemap case, `POST /api/v1/ops/sites/{id}/links` with two URLs.
6. **Expected**: `201` with `source="manual"` candidates.
7. `POST /api/v1/ops/sites/{id}/links/review` keeping some and removing others.
8. **Expected**: kept links are eligible for capture; removed links are recorded as
   `removed` and excluded (SC-006). A review keeping none leaves the site in `onboarding`
   with `link_not_ready` (FR-011).

### V3 — Operator-driven capture — proves FR-012..FR-017, SC-007

1. With the operator's local `domtrack serve` running, `POST /api/v1/ops/links/{id}/captures`
   with `{"mode":"interactive"}`.
2. **Expected**: `201`; a Chrome window opens on the link and recording begins.
3. End the recording; domtrack reports the trace path on the operator's system.
4. `POST /api/v1/ops/captures/{id}/trace` with the file (or `{"local_path": ...}`).
5. **Expected**: `201`; a `Trace` row exists linked to the link, the operator, and the
   capture time, with `is_valid_trace=true` and a UUID-based `storage_key`; the artifact in
   the configured store is unmodified (SC-007).
6. Stop the local domtrack service and trigger capture on another link.
7. **Expected**: `502 domtrack_unreachable`; the link does not advance.
8. Attempt extraction on a link with no stored trace.
9. **Expected**: `409 trace_required` (no advance without a trace, FR-014).

### V4 — Table extraction determinism — proves FR-018..FR-020, SC-008

1. `POST /api/v1/ops/links/{id}/extractions` for a link with a stored trace.
2. **Expected**: `201` with one or more tables stored as `ExtractedTable` records linked to
   the link and trace, each column carrying domtrack's `path` and `coverage`.
3. Repeat the same call.
4. **Expected**: identical rows (same trace ⇒ same tables, SC-008).
5. Run extraction on a trace with no tabular structure.
6. **Expected**: `200` with `table_count=0` and the link moved to `flagged`.

### V5 — Optional labeling — proves FR-021..FR-024, SC-016

1. With labeling at its default (disabled), `POST /api/v1/ops/links/{id}/labeling`.
2. **Expected**: `403 labeling_disabled`; no `SemanticLabel` rows exist, and mapping,
   cleaning, publishing, and replay all still work (0 dependency on labels).
3. Enable labeling as an admin (`PUT /api/v1/ops/settings`) with provider/model/language.
4. `POST /api/v1/ops/links/{id}/labeling`.
5. **Expected**: `200` with meaningful table and column labels stored as `SemanticLabel`
   rows and the call's cost appended to the cost ledger.
6. Lower the LLM cost ceiling below the next call's expected cost
   (`PUT /api/v1/ops/llm-cost-ceiling`) and label again.
7. **Expected**: `409 llm_ceiling_exceeded`; no labels written, the situation is reported,
   and no overspend occurs (FR-024).

### V6 — Merge and mapping in Handsontable — proves FR-025..FR-031, SC-009..SC-010

1. Open `/ops/links/{id}/mapping` (or `GET /api/v1/ops/links/{id}/tables` +
   `GET /api/v1/ops/plan-schema?plan_type=hosting`).
2. **Expected**: the extracted tables render in the Handsontable grid and a dropdown switches
   between tables.
3. Combine fields across two tables and connect each to a schema field; save with
   `PUT /api/v1/ops/links/{id}/recipe`.
4. **Expected**: `200`; the recipe records, per connected field, the source selector (the
   column's domtrack `path`) and an Excel/spreadsheet-valid combination formula; the link
   becomes `mapped` (SC-009).
5. Save a recipe while one required field is unconnected.
6. **Expected**: `409 recipe_incomplete`; the link is not marked mapped and cannot be
   published.
7. Reopen the workspace.
8. **Expected**: previously saved selectors and formulas are restored (FR-031).

### V7 — Cleaning and publishing — proves FR-032..FR-036, SC-011

1. `POST /api/v1/ops/links/{id}/cleaning` on mapped data containing inconsistent units or
   ranges.
2. **Expected**: values are standardized so filters can be applied; automatically cleanable
   data needs no operator action, and only the exceptions are returned (SC-011).
3. `POST /api/v1/ops/links/{id}/publish`.
4. **Expected**: `200`; `catalog` publishes records with provenance to site, link, trace,
   and recipe, and they are available to the main site through `catalog/interfaces.py`
   (FR-034, FR-035).
5. Record a value the cleaner cannot standardize.
6. **Expected**: only that exception is surfaced; the rest of the record is cleaned and
   remains publishable.

### V8 — Scheduled replay, diff, and failure alerting — proves FR-037..FR-042, SC-012..SC-014

1. Set a short replay period in the console settings, then run
   `python manage.py run_scheduled_replays` (or `POST /api/v1/ops/replay-runs`).
2. **Expected**: due links are replayed; each `ReplayRun` records a before trace, a fresh
   after trace from record-during-replay, and a domtrack compare/diff summary that is applied
   to published data (FR-038, FR-039, SC-012).
3. Remove an item from the replayed page (or use a fixture whose diff reports a removal).
4. **Expected**: the corresponding published record is retired rather than retaining a stale
   value (FR-036).
5. Force a link's failure rate past the configured threshold (domtrack reports the failures).
6. **Expected**: one open `FailureAlert` names the link, an in-app notification appears, and
   an email is sent to the configured recipient list — both delivered by the
   `notifications` app; the alert is not repeated on every subsequent replay until it
   resolves (FR-040, FR-041, SC-013).
7. Add and remove a notification recipient as an admin.
8. **Expected**: both operations succeed; removed recipients are deactivated without
   rewriting delivered history.
9. `POST /api/v1/ops/links/{id}/rerun` for the flagged link.
10. **Expected**: the operator can re-run capture → extract → map → clean → publish and the
    link returns to active status (FR-042, SC-014).

## Cross-cutting checks

### Tuning without code changes — proves FR-043, SC-015

Change the replay period, failure-rate threshold, labeling toggle, and cleaning rules through
`GET | PUT /api/v1/ops/settings`; each change takes effect on the next run without a
redeploy. No tunable is hard-coded.

### No reimplementation of domtrack — proves FR-000, SC-017

Run the backend test suite; `admin_console/tests/test_domtrack_reuse.py` must pass, proving
every `domtrack` import lives in `admin_console/domtrack_client.py` and that capture, replay,
record-during-replay, compare, diff, HTML rebuild, table extraction, and labeling are all
served by domtrack.

### Masked logs — proves FR-044, SC-018

Exercise approval, capture, extraction, mapping, publishing, and replay, then inspect the
structured JSON logs: every event is structured, hot paths are sampled/aggregated rather
than logged per item, and no log entry contains a phone number or trace content.
