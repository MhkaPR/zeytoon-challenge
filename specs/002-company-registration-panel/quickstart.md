# Quickstart Validation: Company Registration & Company Panel

A runnable guide to prove the feature works end-to-end. It references
[spec.md](./spec.md), [data-model.md](./data-model.md), and
[contracts/companies-api.md](./contracts/companies-api.md) instead of duplicating their
details.

## Prerequisites

- Python 3.14 with the project virtualenv active; dependencies installed.
- PostgreSQL (or the local SQLite default) and Redis reachable.
- A logged-in user with a valid JWT (from the SMS OTP login feature) who owns no companies.
- An operator account in the `admin` group for recording verification decisions.

## Setup

```bash
# from repo root
cd backend/src
python manage.py startapp companies   # if the scaffold is not present yet
python manage.py startapp panel
python manage.py startapp catalog
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Register the three apps in `INSTALLED_APPS`, mount `/api/v1/companies/` and
`/api/v1/panel/` in `config/urls.py`, and add the constance constants from
[data-model.md](./data-model.md) to `CONSTANCE_CONFIG`.

```bash
# in a second terminal
cd frontend
yarn dev
```

Use the local SQLite/Redis defaults; no SMS gateway is needed for this feature.

## Validation Scenarios

### V1 — Register a company (step one) — proves FR-001..FR-006, SC-001

1. As a user with no companies, open the panel; confirm the empty state with a "Register new
   company" button.
2. Submit `POST /api/v1/companies` with domain, company name, representative name, and phone
   number (leave `internal_number` empty).
3. **Expected**: `201`; a company exists under the caller with `verification_status=pending`
   and `unverified=true`; it appears in `GET /api/v1/companies`.
4. Submit again without `internal_number` and with each mandatory field omitted in turn.
5. **Expected**: valid submission accepted (internal number optional); each missing mandatory
   field returns `400` naming the offending field and creates no company.

### V2 — Multiple companies, single owner — proves FR-006

1. Register a second company as the same user.
2. **Expected**: two distinct companies both owned by the same user; each is independently
   verified, charged, and credited.

### V3 — Append-only verification history — proves FR-013..FR-019, SC-004

1. As an operator, `POST /api/v1/companies/{id}/verification-decisions` with
   `{"outcome": "approved"}`.
2. **Expected**: company becomes `verified`, the full panel is reachable, and exactly one
   verification entry (outcome, actor, time, note) exists.
3. On another pending company, record `not_approved`; **expected**: company stays unverified,
   step one reopens as the current step, and one entry exists.
4. Record a further decision on the first company; **expected**: the earlier entry is
   unchanged and still readable.
5. Attempt to set a company's status as its owner; **expected**: refused.

### V4 — Panel entry, switching, and the continue view — proves FR-022..FR-029, SC-003

1. With verified / pending / rejected companies owned by one user, open the panel and switch
   between them.
2. **Expected**: the verified company opens the full panel; each unverified company opens the
   "Continue company registration" view showing completed steps and the pending step, with a
   route to the current step.
3. Address the full-panel location directly for an unverified company
   (`GET /api/v1/panel/companies/{id}/panel`).
4. **Expected**: `303` redirect to the continue view; the full panel never renders.
5. Switch from a verified to a pending company; **expected**: no full-panel data for the
   pending company is exposed.

### V5 — Mid-step abandonment — proves FR-009, SC-005

1. Start the company-information step, enter partial input, then call
   `POST /api/v1/companies/{id}/steps/company_information/abandon` (or abandon step one before
   submission for a user with no company yet).
2. **Expected**: only that step's unsaved input is cleared; previously saved steps are intact;
   the user resumes at the same step, not step one.

### V6 — Step locking — proves FR-008, FR-011

1. Address the verification step for a company whose step one is not approved.
2. **Expected**: `403` with the configured step-locked message, whether reached by navigation
   or direct address.

### V7 — Listing prerequisites — proves FR-030, FR-031, SC-002

1. In a verified company that is not charged, attempt to create and then activate a listing.
2. **Expected**: `409` with `fields.missing = ["charged"]`, naming the missing prerequisite.
3. In an unverified company, attempt the same; **expected**: `409` with the missing
   prerequisite(s) named — both when both are missing.
4. Charge the company and activate the listing; **expected**: the action succeeds; removing
   the charge afterwards does not silently destroy the listing, and the next listing action
   reports the missing prerequisite.

### V8 — Crawl eligibility and credit — proves FR-034, FR-035, SC-010

1. Enable crawl (`POST /api/v1/companies/{id}/crawl`) while uncharged; **expected**: `409`
   with `fields.missing = ["charged"]`.
2. Charge the company, enable crawl, and record the credit before/after.
3. **Expected**: crawl enables successfully and credit is unchanged (crawl costs nothing).
4. Change one company's charge/credit and confirm the other company's charge/credit is
   unchanged.

### V9 — Duplicate-domain signal — proves FR-041, FR-042, SC-009

1. Register a company whose domain already exists.
2. **Expected**: the submission is accepted with a `duplicate_signal` populated (matched
   domain); it is not blocked and not merged.

### V10 — Ownership and archival — proves FR-036..FR-040, SC-007, SC-008

1. Attempt an in-product ownership transfer; **expected**: `409`.
2. Delete a user account (via the accounts feature) who owns companies and listings.
3. **Expected**: their companies and listings are archived (soft delete), remain retrievable,
   and nothing is hard-deleted; ownership is not transferred automatically.

### V11 — Owner scoping — proves FR-028, SC-006

1. As user A, request a company owned by user B (list, detail, panel entry, listing actions).
2. **Expected**: `404` for every company-scoped request; no company data is returned.

### V12 — Configurable values and log masking — proves FR-045, FR-046, SC-011, SC-012

1. Change a constance constant (e.g. a prerequisite message or step definition) via the
   Django admin, repeat a scenario, and confirm the new value takes effect without code
   changes.
2. Exercise the flows above, then inspect the structured JSON logs.
3. **Expected**: no entry contains a full company phone number; verification decisions,
   listing refusals, and ownership refusals are recorded as structured events.

## Automated Test Entry Points

- Backend: `pytest backend/src/companies/tests backend/src/panel/tests backend/src/catalog/tests`
  (registration, step locking, abandonment, history immutability, panel routing/scoping,
  prerequisites, crawl gating, duplicate signal, archival, masking).
- Frontend: `yarn test` in `frontend/` for the registration forms, continue view, switcher,
  and empty state.

## Success Checklist

- [ ] V1–V12 pass.
- [ ] No `[NEEDS CLARIFICATION]` items remain in the spec.
- [ ] Constitution gates (plan.md) still pass after implementation.
- [ ] No admin-frontend code was added (the admin/operator panel is a separate application).
- [ ] No company is hard-deleted and no verification history entry is ever modified or removed.
