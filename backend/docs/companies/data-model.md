# companies — Data Model

## Company

Table: `companies_company`

| Column | Type | Notes |
|---|---|---|
| `id` | bigint | primary key |
| `owner_id` | FK → `accounts_user` | `PROTECT`; one owner per company |
| `domain` | varchar(255) | normalized on save; crawl seed |
| `company_name` | varchar(255) | |
| `representative_name` | varchar(255) | |
| `phone_number` | varchar(32) | stored as submitted |
| `internal_number` | varchar(32) | optional |
| `verification_status` | varchar(16) | `pending` / `verified` / `rejected` |
| `charge_status` | varchar(16) | `charged` / `not_charged` |
| `crawl_enabled` | bool | requires charged |
| `is_archived` | bool | indexed; never hard-deleted |
| `archived_at` | timestamp | |
| timestamps / `deleted_at` | | inherited |

Relations:

- `owner.companies`
- `step_progress`
- `registration_drafts`
- `verification_decisions`
- `credit_entries`
- `ops_site` (one-to-one, pipeline)

## CompanyStepProgress

Table: `companies_step_progress`

| Column | Type | Notes |
|---|---|---|
| `company_id` | FK | |
| `step_key` | varchar(64) | configured key |
| `order` | smallint | display order |
| `state` | varchar(16) | `locked` / `open` / `saved` / `approved` / `rejected` |
| `last_saved_at` | timestamp | |

Constraint: unique `(company, step_key)` where `deleted_at IS NULL`.

## CompanyRegistrationDraft

Table: `companies_registration_draft`

| Column | Type | Notes |
|---|---|---|
| `owner_id` | FK | draft owner |
| `company_id` | FK, nullable | may be created before a company exists |
| `step_key` | varchar(64) | |
| `payload` | JSON | raw step input |
| `expires_at` | timestamp | optional |

Drafts are not domain records; abandoning a step deletes only that step's drafts.

## VerificationDecision

Table: `companies_verification_decision`

Append-only (`_AppendOnlyMixin`).

| Column | Type | Notes |
|---|---|---|
| `company_id` | FK | |
| `outcome` | varchar(16) | `approved` / `not_approved` |
| `actor_id` | FK → user | `PROTECT` |
| `decided_at` | timestamp | |
| `note` | text | optional |

Ordering: newest decision first. Django admin is read-only for this model.

## CreditLedgerEntry

Table: `companies_credit_ledger_entry`

Append-only (`_AppendOnlyMixin`).

| Column | Type | Notes |
|---|---|---|
| `company_id` | FK | |
| `direction` | varchar(16) | `charge` / `decharge` |
| `amount` | positive int | |
| `reason` | varchar(32) | `payment` / `platform_view` / `adjustment` |
| `reference` | varchar(255) | optional external reference |
| `actor_id` | FK, nullable | `SET_NULL` |

Current credit is computed, not stored:

```text
current_credit = Σ(charge.amount) − Σ(decharge.amount)
```

## Domain normalization

- `normalize_domain()` lowercases, strips scheme/path/query/port, and preserves `www.`.
- `canonical_domain()` additionally strips a leading `www.` for duplicate detection.

Duplicate detection is advisory and only used by the operator approval queue.
