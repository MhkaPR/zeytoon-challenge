# Data Model: Company Wallet and Crawl Eligibility

This is the target model design. It preserves module ownership: `companies` owns wallet
records; the installed `payment` app owns provider transactions; the new `pipeline` app owns
sites, links, traces, and pipeline lifecycle state; `admin_console` owns operator/admin
endpoints and presentation; `catalog` owns published plan records. Cross-app behavior uses
declared interfaces.

## Company (existing, revised)

**Owner**: `companies`

Retain owner, normalized domain, names/contact, verification state, archival state, and audit
timestamps. Remove `charge_status` and `crawl_enabled`. Financial and crawling eligibility are
derived, not separately toggled. Do not add email to the user model; phone remains the user
identity.

## CompanyWallet (new)

**Owner**: `companies`

| Field | Type | Rules |
|---|---|---|
| id | BigAutoField | Primary key |
| company | OneToOne to Company | Required; one wallet per company |
| created_at / updated_at | TimestampedModel fields | Audit timestamps |

The wallet is the aggregate root. Its balance is projected from wallet ledger entries (or may
be cached only as a transactionally maintained projection if profiling justifies it); ledger
entries remain authoritative. Do not duplicate payment provider credentials or gateway status
onto this record.

## WalletEntry (new, append-only)

**Owner**: `companies`

| Field | Type | Rules |
|---|---|---|
| id | BigAutoField | Primary key |
| wallet | ForeignKey to CompanyWallet | Required |
| direction | Choice | Credit or debit |
| amount | Positive integer | Greater than zero; unit documented consistently with payment package |
| reason | Choice | Provider top-up, plan/service charge when separately specified, or admin adjustment |
| payment_transaction_id | Nullable unique reference to payment transaction | Must be unique when present; supports exactly-once credit |
| reference | String | Optional business/audit reference, no secrets |
| actor | Nullable user FK | For authorized manual adjustment attribution |
| created_at / updated_at | TimestampedModel fields | Ledger time |

Entries cannot be updated or deleted. Any balance-changing action creates an entry. A confirmed
provider transaction can create no more than one credit entry. Exact debit rules remain
separate: the current spec defines a minimum-balance eligibility threshold and does not define
per-plan/recurring debits.

## Payment `PayPortal` and `Transaction` (existing third-party package)

**Owner**: installed `payment` app.

Use the package's configured provider portal and transaction lifecycle. Relevant transaction
fields include portal, provider transaction ID, optional user, amount, status, description,
provider metadata, and generic linked content type/object ID. The application links a top-up
transaction to its company wallet and records the corresponding immutable wallet credit only
after provider verification reports success. Package transaction rows are provider payment
records, not wallet ledger entries and not a balance source.

## Charge eligibility (derived, not a persisted flag)

For company `C`, eligible iff all domain requirements are satisfied (including verified and
not archived where existing behavior requires them) and:

`wallet_balance(C) >= CONSTANCE.COMPANY_WALLET_MINIMUM_BALANCE`

The exact configured value and wallet amount use the same documented unit. Return a structured
eligibility result with `eligible`, current balance, required balance, and a stable reason code
(for example `insufficient_balance`, `payment_pending`, `company_unverified`, `company_archived`).
Do not persist `crawl_enabled` or `charge_status` as the source of truth.

## Site and Link (existing, revised)

**Owner**: `pipeline`

- `Site` remains one-to-one with Company, with domain, maintenance state, discovery/replay
  timestamps. Remove the unused per-site `crawl_query`; discovery uses centrally configured
  Constance query values.
- `Link` remains a site-scoped URL with normalized URL hash and unique `(site, url_hash)`.
  `source` distinguishes adaptive discovery from manual company submission. Review and
  pipeline states remain independent of financial eligibility.

Pipeline model classes and their migrations live in `pipeline.models` and
`pipeline.migrations`. Operator/admin views must obtain pipeline records and invoke actions via
`pipeline.interfaces`; they must not import pipeline models directly. Preserve the existing
database rows and stable table names as the app ownership is transferred.

## PublishedRecord (existing, revised)

**Owner**: `catalog`

Keep plan values, plan type, natural key, provenance identifiers, publication and retirement
timestamps. Ensure public reads resolve each record's company eligibility through a declared
catalog/companies interface contract. `is_published` is necessary publication state but
insufficient by itself to make a record publicly retrievable. Eligibility loss withdraws all
company plan records; eligibility restoration only republishes records that remain valid and
quality approved.

## Eligibility transition and lifecycle

1. Start a provider payment: create a payment-package `Transaction` linked to the company
   wallet and redirect using the selected portal backend.
2. Verify the provider result: only a verified successful transaction is eligible to produce
   a wallet credit; enforce uniqueness by payment transaction reference inside a database
   transaction.
3. Recompute eligibility from the wallet ledger and Constance threshold.
4. On eligible → ineligible, withdraw every public plan, invalidate public/search caches, and
   ensure queued tasks recheck before external work. On ineligible → eligible, allow crawl and
   replay scheduling and republish only still-valid quality-approved plans.
5. Every `pipeline` task rechecks eligibility at execution; store auditable transition/skip outcomes
   without logging full phone numbers or provider secrets.

## Migration and data transition

- Create one wallet for each existing company.
- Map existing company credit ledger totals into wallet entries, preserving direction, amount,
  reason, reference, actor, and chronology where valid.
- Convert legacy charge state only as migration input; final eligibility is recomputed from
  the mapped wallet balance and configured threshold. Never treat the old flag as enduring
  authority.
- Remove legacy charge/crawl flags and APIs after callers are migrated.
- Remove `Site.crawl_query`; retain global Constance discovery query configuration.
- Preserve existing published records and provenance; reconcile their visibility against the
  new eligibility result.
- Preserve payment identity and account history; display full phone in authorized displays.

## Integrity rules

- One CompanyWallet per Company.
- Wallet entry amount is positive and immutable.
- At most one wallet credit per confirmed payment transaction.
- Provider transaction amounts satisfy the installed package's validation requirements and
  wallet amount unit contract.
- Each Link remains unique by normalized `(site, url_hash)` regardless of source.
- A manually submitted URL must belong to the company's registered domain and pass the same
  normalization/policy checks as automated discovery.
- Catalog public response includes only quality-approved, published records for currently
  eligible companies.
