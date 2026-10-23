# Contract: Company Registration & Panel API (v1)

Base path: `/api/v1/companies`. Everything in this feature — registration, the panel
entry/switching surface, verification decisions, the plan-eligibility gate, credit, and crawl
— is served by the single `companies` module (there is no separate `panel` app). JSON in, JSON
out. All timestamps ISO-8601 UTC. Error bodies use the existing shared shape
(`accounts.exceptions`) — this contract is the reviewed source of intent; the generated
OpenAPI schema (drf-spectacular) is the machine-readable form.

## Conventions

- Authentication: `Authorization: Bearer <access_token>` on every endpoint here (JSON Web
  Token auth from the `accounts` feature, Principle XI). Unauthenticated requests get `401`.
- Authorization: every company-scoped request is restricted to companies the caller owns; a
  company the caller does not own is `404` (treated as not found, FR-028, SC-006).
- CSRF: state-changing requests MUST include `X-CSRFToken` matching the CSRF cookie.
- Operator endpoints: the verification-decision endpoint requires the `admin` role; company
  owners MUST NOT be able to record their own decisions (FR-012, FR-019).
- Masking: no response or log includes a full company phone number except the owner's own
  value echoed back masked (FR-046).

### Error shape

```json
{
  "error": {
    "code": "company_requirement_missing",
    "message": "This action needs the company to be verified and charged.",
    "fields": { "missing": ["charged"] }
  }
}
```

## Company registration

### POST /api/v1/companies

Submit the company-information step (step one) and create the company.

**Request**

```json
{
  "domain": "example.com",
  "company_name": "Example Hosting",
  "representative_name": "Ali Rezaei",
  "phone_number": "02123456789",
  "internal_number": "105"
}
```

`internal_number` is optional; all other fields are mandatory.

**Responses**

| Status | Meaning | Body |
|--------|---------|------|
| 201 | Company created, pending verification | `{ "company": { "id", "domain", "company_name", "verification_status": "pending", "unverified": true }, "step_progress": {...} }` |
| 400 | Missing/invalid mandatory field | error `code: "invalid_field"`, `fields` names the offending field(s); no company created (FR-003) |
| 401 | Not authenticated | error `code: "not_authenticated"` |

**Rules**
- On success the company is owned by the submitting user with `verification_status=pending`
  and appears in the owner's company list flagged unverified (FR-004, FR-005).
- A user may submit repeatedly to create additional companies; each is a distinct record
  (FR-001, FR-006).
- The `domain` is stored normalized so the admin panel can detect duplicates; this feature
  performs no detection, produces no signal, and never auto-blocks or auto-merges (FR-041, FR-042).

### GET /api/v1/companies

List the caller's companies (for the switcher and list view).

| Status | Meaning | Body |
|--------|---------|------|
| 200 | OK | `{ "companies": [ { "id", "domain", "company_name", "verification_status", "unverified", "charge_status", "current_step" } ] }`. Only the caller's companies are returned (FR-028). |

### GET /api/v1/companies/{id}

Company detail plus step progress for the owner.

| Status | Meaning | Body |
|--------|---------|------|
| 200 | OK | `{ "company": {...}, "step_progress": [ { "step_key", "order", "state", "completed": bool } ], "current_step": "verification" }` (FR-010, FR-026). |
| 404 | Not owned / not found | error `code: "not_found"` (FR-028). |

### POST /api/v1/companies/{id}/steps/{step_key}/abandon

Abandon the current step half-finished.

**Rules**
- Clears only that step's unsaved draft; previously saved steps are untouched; the response
  returns the user to the same step (FR-009, SC-005).

| Status | Meaning | Body |
|--------|---------|------|
| 200 | Draft cleared | `{ "step_key": "company_information", "resume_at": "company_information", "drafts_cleared": ["company_information"] }` |
| 403 | Step locked | error `code: "step_locked"` (FR-008). |
| 404 | Not owned / not found | error `code: "not_found"`. |

## Verification (operator-decided; UI out of scope)

### POST /api/v1/companies/{id}/verification-decisions

Record a verification decision. Operator-only; the company owner is refused.

**Request**

```json
{ "outcome": "approved", "note": "Called and confirmed registration details." }
```

**Responses**

| Status | Meaning | Body |
|--------|---------|------|
| 201 | Decision recorded | `{ "company_id", "verification_status": "verified", "decision": { "outcome", "actor", "decided_at", "note" } }` |
| 200 | Decision recorded, not approved | `{ ..., "verification_status": "rejected", "current_step": "company_information" }` (step one reopens, FR-015, FR-020) |
| 403 | Caller is not an operator / is the owner | error `code: "not_permitted"` (FR-012). |
| 404 | Company not found | error `code: "not_found"`. |
| 422 | Invalid outcome | error `code: "invalid_outcome"` (FR-013). |

**Rules**
- Every decision appends exactly one immutable history entry (outcome, actor, time, note) and
  never alters earlier entries (FR-016, FR-017, SC-004).
- This endpoint is the only path that changes `verification_status` (FR-019).
- Approval makes the full panel reachable; not-approved keeps the company unverified and
  reopens step one (FR-014, FR-015).

## Company panel

### GET /api/v1/companies/{id}/panel-entry

Resolve what the panel should render for the selected company.

| Status | Meaning | Body |
|--------|---------|------|
| 200 | Owner, verified | `{ "view": "full_panel", "company": {...} }` (FR-024). |
| 200 | Owner, pending/rejected | `{ "view": "continue_registration", "company": {...}, "step_progress": [...], "current_step": "verification", "verification_status": "pending" }` (FR-025, FR-026). |
| 404 | Not owned / not found | error `code: "not_found"` (FR-028). |

### GET /api/v1/companies/{id}/panel

The full company panel location.

| Status | Meaning | Body |
|--------|---------|------|
| 200 | Verified owner | full-panel payload (FR-024). |
| 303 | Owner, unverified | `Location: /api/v1/companies/{id}/panel-entry`; the full panel is NOT rendered (FR-027, SC-003). |
| 404 | Not owned / not found | error `code: "not_found"`. |

**Rules**
- Direct addressing of the full-panel location for an unverified company always redirects to
  the continue view; the full panel never renders with real data for it (FR-027, edge case
  "Direct address").

### GET /api/v1/companies/panel-switcher

Data for the switcher; when the caller owns no companies the payload supports the empty state.
This is a distinct path from `GET /api/v1/companies` (the plain list) so the switcher payload
carries the empty-state contract.

| Status | Meaning | Body |
|--------|---------|------|
| 200 | No companies | `{ "companies": [], "empty_state": true, "message": "<configured>" }` (FR-023). |
| 200 | Has companies | `{ "companies": [ { "id", "company_name", "verification_status", "unverified" } ], "empty_state": false }` (FR-022). |

**Rules**
- Switching companies must not expose one company's verification, charge, credit, or plan
  data while another is selected; every panel read is scoped to a single company (FR-029).

## Plan eligibility and credit

Plans (host/server offerings) are owned by another feature; there is **no plan endpoint
here**. This feature exposes only the eligibility gate that a plan-owning feature calls, plus
the per-company credit ledger and the crawl flag.

### GET /api/v1/companies/{id}/plan-eligibility

Evaluate whether plan actions are allowed for this company (FR-030, FR-031).

| Status | Meaning | Body |
|--------|---------|------|
| 200 | Allowed | `{ "allowed": true, "missing": [] }` |
| 200 | Blocked | `{ "allowed": false, "missing": ["verified", "charged"], "message": "<configured>" }` — `missing` lists **every** unsatisfied prerequisite; when both are missing both are named (SC-002). |
| 404 | Not owned / not found | error `code: "not_found"`. |

**Rules**
- `allowed` is true only when the company is `verified` **and** `charged` (FR-030).
- The gate is read-only; it creates or activates no plan (the plan feature owns that).
- Existing plans are not silently destroyed when charge is removed; the gate reports the
  missing prerequisite the next time a plan action is evaluated (edge case "Charge removed
  after plans exist").

### GET /api/v1/companies/{id}/credit

Read the company's current credit and its ledger (FR-034).

| Status | Meaning | Body |
|--------|---------|------|
| 200 | OK | `{ "current_credit": 1200, "currency": "credit", "entries": [ { "id", "direction": "charge"\|"decharge", "amount", "reason", "created_at" } ] }` — `current_credit` is the projection (running total) of the entries; entries are returned newest-first. |
| 404 | Not owned / not found | error `code: "not_found"`. |

**Rules**
- The ledger is append-only: entries are never altered or removed, and every charge/decharge
  movement is exactly one entry (FR-034, SC-013).
- Credit is per company; the ledger never includes another company's movements (FR-033).
- Metered platform views (owned by the views/search features) append `decharge` entries;
  enabling crawl and crawl traffic append none (FR-034a, FR-035).

### POST /api/v1/companies/{id}/credit/movements

Record a charge or decharge movement. Called by the owning features (payment for top-ups,
views for metered consumption); operator `adjustment` allowed for the admin actor.

**Request**

```json
{ "direction": "charge", "amount": 1000, "reason": "payment", "reference": "pay_123" }
```

| Status | Meaning | Body |
|--------|---------|------|
| 201 | Recorded | `{ "entry": { "direction", "amount", "reason", "created_at" }, "current_credit": 2200 }` |
| 400 | Invalid movement (non-positive amount, unknown reason) | error `code: "invalid_movement"`. |
| 403 | Not permitted for this reason | error `code: "not_permitted"`. |
| 404 | Not owned / not found | error `code: "not_found"`. |

**Rules**
- Exactly one append-only entry is created per movement; the response returns the recomputed
  projection (FR-034, SC-013).
- Enabling crawl MUST NOT be expressed as a credit movement (FR-034a, FR-035).

### POST /api/v1/companies/{id}/crawl

Enable crawling for the company (free; requires a charged account).

**Request**

```json
{ "enabled": true }
```

| Status | Meaning | Body |
|--------|---------|------|
| 200 | Enabled/disabled | `{ "crawl_enabled": true, "credit_unchanged": true }` |
| 409 | Not charged | error `code: "company_requirement_missing"`, `fields.missing = ["charged"]` (FR-035). |
| 404 | Not owned / not found | error `code: "not_found"`. |

**Rules**
- Enabling crawl never consumes credit (edge case "Crawl enabled then account becomes
  uncharged"; FR-035); only platform views consume credit (FR-034, FR-034a).

## Ownership and governance hooks

- **Ownership transfer**: any in-product attempt returns `409` error
  `code: "ownership_transfer_unsupported"` directing the user to the admin-coordinated manual
  process; no path changes ownership automatically (FR-036, FR-037, SC-008).
- **Duplicate detection**: out of scope; the admin panel owns it. The company domain is stored
  normalized so the admin panel can match it, and no signal model or endpoint exists here
  (FR-041, FR-042, SC-009).
- **Archival**: deleting a user account (handled by the `accounts` feature) archives that
  user's companies; archived companies remain retrievable and are never hard-deleted (FR-038,
  FR-039, FR-040).
- **Abuse hooks**: company state (verification, charge, credit, archival) is readable by the
  admin-side actor; this feature exposes no admin management tooling (FR-043, FR-044).

## Cross-cutting behaviors

- **Scoping**: every company-scoped request checks ownership; non-owned companies are `404`
  (FR-028, SC-006).
- **Logging**: verification decisions, plan-prerequisite refusals, credit movements, and
  ownership-transfer refusals emit structured JSON events with masked phone numbers (FR-046,
  SC-012).
- **Configuration**: messages and step definitions come from django-constance constants, so
  operators can change them at runtime without code changes (FR-045, SC-011).
- **Out of scope**: no admin-panel/operator UI, ticket, crawl-engine, payment/charging, plan
  management, duplicate detection, or search/ranking endpoints exist here (FR-044).
