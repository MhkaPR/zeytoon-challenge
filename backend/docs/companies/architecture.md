# companies — Architecture

## 1. Responsibility

`apps.companies` owns the provider side of the product:

- multi-step company registration with locked steps;
- operator verification decisions and append-only history;
- the company panel entry/switcher surface;
- plan eligibility gating (verified + charged);
- the append-only credit ledger and current-credit projection;
- crawl enablement and manual link submission;
- ownership-transfer refusal and company archival.

There is no separate `panel` app; panel behavior lives here.

## 2. Internal layout

| Path | Responsibility |
|---|---|
| `models/company.py` | `Company` aggregate and domain normalization |
| `models/step_progress.py` | per-company step state and locking |
| `models/registration_draft.py` | short-lived per-step drafts |
| `models/verification.py` | append-only `VerificationDecision` |
| `models/credit.py` | append-only `CreditLedgerEntry` |
| `models/append_only.py` | insert-only mixin |
| `domain.py` | `normalize_domain`, `canonical_domain` |
| `steps.py` | step enterability/locking checks |
| `constants.py` | constance-backed step definitions and messages |
| `selectors.py` | owner scoping, step resolution, credit projection, approval payloads |
| `services/v1/companies.py` | registration, abandon, verification, eligibility, credit, archival |
| `events.py` | structured company events |
| `signals.py` | account-deletion archival hook |
| `interfaces.py` | `CompaniesInterface` |
| `views/v1/companies.py` | company/panel/verification/credit/link endpoints |

## 3. Domain model

```text
User 1 ─── * Company 1 ─── * CompanyStepProgress
                 │
                 ├── * CompanyRegistrationDraft
                 ├── * VerificationDecision   (append-only)
                 ├── * CreditLedgerEntry      (append-only)
                 └── 1 Site                  (pipeline, created on approval)
```

A company is owned by exactly one user, is never hard-deleted, and is archived instead.

## 4. Registration steps

Steps are configured in `COMPANY_STEP_DEFINITIONS` (constance):

1. `company_information` — owner input; approved on creation.
2. `verification` — operator input; locked until step one is approved.

`CompanyStepProgress.state` is one of `locked`, `open`, `saved`, `approved`, `rejected`.

`steps.assert_step_enterable()` enforces:

- the step key exists;
- the row is not locked;
- for non-first steps, the previous step is approved.

`selectors.current_step()` returns the first configured step that is not approved, or
`None` when registration is complete.

## 5. Verification

`services.record_verification_decision()` is the only write path:

- appends a `VerificationDecision` with outcome, actor, timestamp, note;
- `approved`: company becomes `verified`, verification step becomes `approved`;
- `not_approved`: company becomes `rejected`, company-information step reopens,
  verification step re-locks.

The owner can never decide their own verification; the view enforces admin role and
rejects `company.owner_id == actor.pk`.

## 6. Plan eligibility and credit

`can_manage_plans()` requires both:

- `verification_status == verified`;
- `charge_status == charged`.

It returns `{allowed, missing, message}` naming every missing prerequisite.

Credit is append-only:

- `CreditLedgerEntry.direction` is `charge` or `decharge`;
- `reason` is `payment`, `platform_view`, or `adjustment`;
- current credit is the running projection `sum(charge) - sum(decharge)`.

Enabling crawl requires a charged company but does not change credit.

## 7. Ownership and archival

- `refuse_ownership_transfer()` always raises `ownership_transfer_unsupported` (409).
- `archive_companies_for_user()` sets `is_archived`/`archived_at`; it never deletes.
- `signals.py` listens for user deletion and archives the user's companies. Because
  `Company.owner` uses `on_delete=PROTECT`, the hook documents and tests the archival path
  rather than performing a physical delete.

## 8. Cross-app dependencies

- `apps.accounts` for caller identity and `ApiError`.
- `apps.pipeline` for manual link submission (`Site`, discovery policy, pipeline task).
- `apps.admin_console` serializer (`ManualLinksInput`) is reused by the links endpoint.
- `CompaniesInterface` is consumed by `admin_console` and `pipeline`.
