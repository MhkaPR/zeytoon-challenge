# companies — Workflow

## 1. Register a company

`POST /api/v1/companies`

```text
validate mandatory fields:
  domain, company_name, representative_name, phone_number
  + normalize_domain(domain)
create Company(owner=caller, verification_status=pending, charge_status=not_charged)
seed step progress:
  company_information = approved
  verification        = locked
emit company_registered
```

The domain is stored normalized (lowercase, scheme/path/query stripped) because it is also
the crawl seed. Duplicate detection is advisory and lives in the operator approval queue.

## 2. Step save / abandon

```text
save_step(user, company, step_key, payload)
  → assert_step_enterable
  → mark step saved
  → append CompanyRegistrationDraft(owner, company, step_key, payload)

abandon_step(user, company, step_key)
  → assert_step_enterable
  → delete only drafts for (owner, company, step_key)
  → if step was saved, set it back to open
  → current_step stays the same, so the user resumes in place
```

Earlier approved steps are never cleared.

## 3. Verification decision

`POST /api/v1/companies/{id}/verification-decisions` (admin only)

```text
caller must be authenticated and role == admin
company must exist
caller must not be the owner

approved:
  append VerificationDecision
  company.verification_status = verified
  verification step = approved

not_approved:
  append VerificationDecision
  company.verification_status = rejected
  company_information step = open
  verification step = locked
```

The operator console wraps this with site onboarding/suspension and pipeline enqueueing.

## 4. Panel entry and switching

```text
GET /companies/panel-switcher
  → caller's companies
  → empty_state + configured message when none

GET /companies/{id}/panel-entry
  → verified:   view = full_panel
  → unverified: view = continue_registration
                includes step_progress, current_step, verification_status

GET /companies/{id}/panel
  → unverified: 303 redirect to /panel-entry
  → verified:   company detail + step progress + plan eligibility
```

## 5. Plan eligibility

`GET /companies/{id}/plan-eligibility`

```json
{
  "allowed": false,
  "missing": ["verified", "charged"],
  "message": "Company must be verified and charged."
}
```

The message is selected from `COMPANY_REQUIREMENT_MESSAGES`.

## 6. Credit ledger

```text
GET  /companies/{id}/credit
  → current_credit = charge - decharge
  → entries (append-only history)

POST /companies/{id}/credit/movements
  → validate direction, reason, amount > 0
  → append CreditLedgerEntry
  → emit company_credit_movement
```

## 7. Crawl and manual links

```text
POST /companies/{id}/crawl
  → enabling requires charge_status == charged
  → set crawl_enabled
  → credit unchanged

POST /companies/{id}/links
  → get_or_create Site(company, domain)
  → apply same-host/deny-list link policy
  → add links manually
  → enqueue run_site_pipeline_task(site, discover=False) on commit
```

## 8. Ownership transfer and archival

```text
POST /companies/{id}/transfer-ownership
  → always 409 ownership_transfer_unsupported
  → emit ownership_transfer_refused

account deletion hook
  → archive all non-archived companies for the user
  → emit company_archived_for_user
```

## 9. Error codes

| Code | Status | Meaning |
|---|---|---|
| `not_authenticated` | 401 | no valid Bearer token |
| `not_found` | 404 | company missing or not owned by caller |
| `invalid_field` | 400 | missing/invalid company fields |
| `unknown_step` | 404 | step key not configured |
| `step_locked` | 403 | previous step not approved |
| `not_permitted` | 403 | non-admin or owner self-decision |
| `invalid_outcome` | 400 | unknown verification outcome |
| `company_requirement_missing` | 409 | crawl enabled without charge |
| `ownership_transfer_unsupported` | 409 | transfer always refused |
