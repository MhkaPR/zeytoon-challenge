# Data Model: Company Registration & Company Panel

Entities extracted from [spec.md](./spec.md) Key Entities and Functional Requirements.
All persistent domain models inherit `utils.models.TimestampedModel` (audit timestamps).
Field types are indicative; exact column types follow Django conventions.

## Company

The registrable business entity, owned by exactly one user. Never hard-deleted.

| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | Primary key. |
| owner | FK → `accounts.User` | Non-null; exactly one owner (FR-006, FR-036). Never changed automatically. |
| domain | CharField (indexed) | Normalized company domain; the practical duplicate-detection key (FR-041). |
| company_name | CharField | Mandatory (FR-002). |
| representative_name | CharField | Mandatory (FR-002). |
| phone_number | CharField | Company phone number; mandatory (FR-002). Masked in logs. |
| internal_number | CharField (blank) | Optional extension dialled after the company phone number (FR-002). |
| verification_status | CharField choices | `pending` / `verified` / `rejected` (FR-004, FR-013, FR-014, FR-015). |
| charge_status | CharField choices | `charged` / `not_charged`; externally set, read-only here (FR-032). |
| credit | PositiveIntegerField | Per-company allowance reduced only by platform views (FR-033, FR-034). Not touched by crawl. |
| crawl_enabled | BooleanField | Per-company crawl switch; requires `charged` (FR-035). |
| is_archived | BooleanField | Soft-delete flag set when the owner's account is deleted (FR-038, FR-039). |
| archived_at | DateTimeField (null) | When archival occurred. |

**Validation rules**
- `domain`, `company_name`, `representative_name`, `phone_number` are mandatory; a missing or
  invalid field rejects the submission naming the field and creates no company (FR-003).
- `verification_status` transitions only through a recorded verification decision (FR-019).
- Ownership is never mutated by any in-product request (FR-036, FR-037).

**State transitions (verification)**

```text
(no company) --submit step one--> pending
pending --decision: approved--> verified      (full panel opens, FR-014)
pending --decision: not approved--> rejected  (step one reopens, FR-015, FR-020)
rejected --resubmit step one--> pending        (repeatable, no cooldown, FR-020)
```

**Archival**: any state → `is_archived=true` when the owner's account is deleted; the record
remains retrievable and is never hard-deleted (FR-038, FR-039, FR-040).

## Registration Step & CompanyStepProgress

Registration is a fixed, ordered step sequence; each step is a standalone form with its own
save and lock state (FR-007, FR-008, FR-010, FR-011).

**Step sequence** (resolved from django-constance step definitions, R1/R9)

| Order | Step | Requires owner input | Unlocked by |
|-------|------|----------------------|-------------|
| 1 | Company information | Yes | Start of registration |
| 2 | Verification | No (operator-decided, FR-011, FR-012) | Step 1 approved |

`CompanyStepProgress` (one row per company × step):

| Field | Type | Notes |
|-------|------|-------|
| company | FK → Company | Owning company. |
| step_key | CharField | Step identifier (`company_information`, `verification`). |
| order | PositiveSmallIntegerField | Resolved from the step definition. |
| state | CharField choices | `locked` / `open` / `saved` / `approved` / `rejected`. |
| last_saved_at | DateTimeField (null) | Last successful save for this step. |

**Validation rules**
- A step is enterable only when its predecessor is `approved`; otherwise access returns a
  refusal even by direct address (FR-008, edge case "Step locking").
- The current step is the first step whose predecessor is approved and which is not itself
  `approved` (FR-010, FR-026).
- The verification step never requires owner input (FR-011).

## CompanyRegistrationDraft

Short-lived store for in-progress **unsubmitted** step input, so abandonment clears only that
step (FR-009, R2).

| Field | Type | Notes |
|-------|------|-------|
| owner | FK → `accounts.User` | Draft owner. |
| step_key | CharField | Which step the draft belongs to. |
| company | FK → Company (null) | Set once a company exists (steps after step one). |
| payload | JSONField | The partial form input for that step only. |
| expires_at | DateTimeField | TTL-driven cleanup; drafts are not domain records. |

**Validation rules**
- Abandoning a step clears only the draft for that (owner, step); saved results of earlier
  steps are untouched and the user resumes at the same step (FR-009, SC-005).
- A draft never blocks or auto-creates a company.

## VerificationDecision (append-only history)

One immutable row per verification outcome (FR-016, FR-017, FR-018, SC-004).

| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | Primary key. |
| company | FK → Company | Decision subject. |
| outcome | CharField choices | `approved` / `not_approved` (FR-013). |
| actor | FK → `accounts.User` | The deciding operator (never the owner, FR-012). |
| decided_at | DateTimeField | Decision time. |
| note | TextField (blank) | Recorded reason/note from the operator (retained internally, not shown in the continue view, FR-021). |
| created_at | DateTimeField | Inherited; insert-only. |

**Validation rules**
- Rows are insert-only: updates and deletes are rejected at the model layer; later decisions
  never alter earlier ones (FR-017, SC-004, edge case "Approval after an earlier rejection").
- A decision writes the company's `verification_status` atomically and is the only path to a
  status change (FR-019).
- The owner cannot create or influence a decision (FR-012, FR-018).

## CompanyDuplicateSignal

Detection-only signal for the admin (FR-041, FR-042, R7).

| Field | Type | Notes |
|-------|------|-------|
| company | FK → Company | The newly submitted company. |
| matched_company | FK → Company | The existing company with the same normalized domain. |
| domain | CharField | The matched domain, for review convenience. |
| created_at | DateTimeField | Inherited. |

**Validation rules**
- Produced on exact normalized-domain match; the submission is still accepted and never
  auto-blocked or merged (FR-042, SC-009).
- Resolution remains the admin's responsibility; no dedup engine exists in this feature.

## Listing (owned by the `catalog` module)

A company's published offer (FR-030, FR-038, FR-039).

| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | Primary key. |
| company | FK → Company | Owning company. |
| title | CharField | Offer title. |
| status | CharField choices | `draft` / `active` / `archived`. |
| is_archived | BooleanField | Set when the company is archived; never hard-deleted (FR-039). |

**Validation rules**
- Create/activate is allowed only when the company is verified **and** charged; the response
  names every missing prerequisite (FR-030, FR-031, SC-002).
- Existing listings are not silently destroyed when charge is removed; whether they stay
  active is reported to the user when they next attempt a listing action (edge case "Charge
  removed after listings exist").
- Archived with the company, never hard-deleted (FR-040).

## Crawl Setting

Represented by `Company.crawl_enabled` (no separate table). Enabling requires a charged
account, costs nothing, and consumes no credit (FR-035, R6).

**Validation rules**
- Enabling is refused with the missing charge prerequisite when the company is not charged.
- Enabling never mutates `Company.credit` (edge case "Crawl enabled then account becomes
  uncharged").

## Abuse State / Hook

Exposed as read state + hooks, not a management tool (FR-043, FR-044). The company's
verification status, charge status, and archival state are readable by the admin-side actor;
this feature provides no admin UI or fraud tooling.

## Runtime configuration: django-constance (database constants)

No custom settings model. Tunables are declared in `CONSTANCE_CONFIG` and stored in the
constance table (Principle XIII, FR-045, SC-011).

| Constant | Default | Purpose |
|----------|---------|---------|
| COMPANY_STEP_DEFINITIONS | ordered list | The step sequence (keys, order, owner-input flag). |
| COMPANY_REQUIREMENT_MESSAGES | mapping | Prerequisite messages (verified/charged) surfaced on listing blocks. |
| COMPANY_DUPLICATE_SIGNAL_MESSAGE | text | Message shown when a duplicate domain is detected. |
| COMPANY_STEP_LOCKED_MESSAGE | text | Message shown when a locked step is addressed. |
| COMPANY_EMPTY_STATE_MESSAGE | text | Copy for the no-companies empty state. |

**Notes**
- Values that must not change at runtime (e.g. DB connection, JWT lifetimes) stay in
  `settings.py` and are environment-driven (Principle XIII).
- Defaults are the documented values from the spec's Assumptions section.

## Relationships

- `User` 1—* `Company` (owner); single-owner, ownership change is admin-only (FR-006, FR-036).
- `Company` 1—* `CompanyStepProgress` (one row per step).
- `Company` 1—* `VerificationDecision` (append-only, immutable).
- `Company` 1—* `CompanyDuplicateSignal` (as the new company and as `matched_company`).
- `User` 1—* `CompanyRegistrationDraft`; `Company` 0..1—* `CompanyRegistrationDraft`.
- `Company` 1—* `Listing` (owned by `catalog`; archived with the company).
- Constance constants are standalone key/value entries consumed by services, not FK-related.

## Out of Scope (explicitly)

- No admin-panel/operator-interface entities, no ticket entities, no crawl-engine entities,
  no payment/charging entities, and no search/ranking entities (FR-044).
- No deduplication/merge engine and no automatic ownership-transfer entity.
- No credit-consumption metering implementation (owned by views/search features); only the
  per-company credit field and read contract are in scope.
