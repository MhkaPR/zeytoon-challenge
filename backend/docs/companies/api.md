# companies — API

Base path: `/api/v1/companies`

All endpoints require a valid Bearer access token. Company-scoped endpoints only see
companies owned by the caller; a non-owned company is reported as `404 not_found`.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | list caller's companies |
| `POST` | `/` | register a company (step one) |
| `GET` | `/{id}` | company detail + step progress + current step |
| `POST` | `/{id}/steps/{step_key}/abandon` | clear only that step's draft |
| `GET` | `/panel-switcher` | companies for the panel switcher |
| `GET` | `/{id}/panel-entry` | full panel vs continue-registration |
| `GET` | `/{id}/panel` | full panel (verified only; 303 otherwise) |
| `POST` | `/{id}/verification-decisions` | operator decision (admin only) |
| `GET` | `/{id}/plan-eligibility` | prerequisite gate |
| `GET` | `/{id}/credit` | current credit + ledger entries |
| `POST` | `/{id}/credit/movements` | append a charge/decharge |
| `POST` | `/{id}/crawl` | enable/disable crawl |
| `POST` | `/{id}/links` | submit additional same-domain links |
| `POST` | `/{id}/transfer-ownership` | always refused (409) |

## Register

`POST /`

```json
{
  "domain": "example.com",
  "company_name": "Example Co",
  "representative_name": "Sara Ahmadi",
  "phone_number": "02112345678",
  "internal_number": "102"
}
```

Response `201`:

```json
{
  "company": {
    "id": 1,
    "domain": "example.com",
    "company_name": "Example Co",
    "representative_name": "Sara Ahmadi",
    "phone_number": "02112345678",
    "internal_number": "102",
    "verification_status": "pending",
    "charge_status": "not_charged",
    "crawl_enabled": false,
    "is_archived": false,
    "unverified": true
  },
  "step_progress": [
    {"step_key": "company_information", "order": 1, "state": "approved", "completed": true},
    {"step_key": "verification", "order": 2, "state": "locked", "completed": false}
  ]
}
```

## Detail

`GET /{id}`

```json
{
  "company": {},
  "step_progress": [],
  "current_step": "verification"
}
```

## Abandon a step

`POST /{id}/steps/{step_key}/abandon`

```json
{
  "step_key": "company_information",
  "resume_at": "company_information",
  "drafts_cleared": ["company_information"]
}
```

## Panel entry

`GET /{id}/panel-entry`

Verified:

```json
{"view": "full_panel", "company": {}}
```

Unverified:

```json
{
  "view": "continue_registration",
  "company": {},
  "step_progress": [],
  "current_step": "verification",
  "verification_status": "pending"
}
```

## Verification decision

`POST /{id}/verification-decisions` — admin role required, owner forbidden.

```json
{"outcome": "approved", "note": "Documents verified"}
```

Response `201` when the company becomes verified, otherwise `200`:

```json
{
  "company_id": 1,
  "verification_status": "verified",
  "current_step": null,
  "decision": {
    "outcome": "approved",
    "actor_id": 7,
    "decided_at": "2026-01-01T10:00:00+03:30",
    "note": "Documents verified"
  }
}
```

## Plan eligibility

`GET /{id}/plan-eligibility`

```json
{"allowed": true, "missing": [], "message": ""}
```

## Credit

`GET /{id}/credit`

```json
{
  "current_credit": 250000,
  "entries": [
    {"id": 1, "direction": "charge", "amount": 300000, "reason": "payment", "reference": "INV-1"},
    {"id": 2, "direction": "decharge", "amount": 50000, "reason": "platform_view", "reference": ""}
  ]
}
```

`POST /{id}/credit/movements`

```json
{"direction": "charge", "amount": 100000, "reason": "adjustment", "reference": "ADJ-1"}
```

## Crawl

`POST /{id}/crawl`

```json
{"enabled": true}
```

Response:

```json
{"crawl_enabled": true, "credit_unchanged": true}
```

Enabling without `charge_status == charged` returns `409 company_requirement_missing`.

## Manual links

`POST /{id}/links`

```json
{"urls": ["https://example.com/plans", "https://example.com/vps"]}
```

Response `201`:

```json
{"links": []}
```

Links are filtered by the same-host/deny-list policy, then the site pipeline is enqueued
without rediscovery.

## Ownership transfer

`POST /{id}/transfer-ownership` always returns `409` with
`ownership_transfer_unsupported`.
