# admin_console — API

Base path: `/api/v1/ops`

All endpoints require an operator (`ops` or `admin`) Bearer token.

## Approvals

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/approvals` | pending company approval queue |
| `POST` | `/companies/{company_id}/verification-decisions` | approve/reject a company |

Decision body:

```json
{"outcome": "approved", "note": "Documents verified"}
```

Response:

```json
{
  "company": {},
  "decision": {},
  "site": {"id": 1, "company_id": 1, "domain": "example.com", "maintenance_state": "onboarding", "onboarded_at": "..."}
}
```

## Sites and links

| Method | Path | Purpose |
|---|---|---|
| `GET/POST` | `/sites` | list sites / onboard a company site |
| `GET` | `/sites/{site_id}` | site detail + links |
| `POST` | `/sites/{site_id}/discover-links` | run adaptive discovery |
| `GET/POST` | `/sites/{site_id}/links` | list links / add manual links |

Onboard body:

```json
{"company_id": 1}
```

Discover body (optional bounds):

```json
{"max_pages": 60, "max_depth": 5}
```

Manual links body:

```json
{"urls": ["https://example.com/plans"]}
```

## Capture

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/links/{link_id}/captures` | start a headless capture |
| `GET` | `/links/{link_id}/captures/list` | list capture sessions |
| `POST` | `/captures/{capture_session_id}/fail` | mark a session failed |

Capture body:

```json
{"duration_ms": 15000}
```

## Extraction and classification

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/links/{link_id}/extractions` | extract tables |
| `GET` | `/links/{link_id}/tables` | table payload |
| `GET/POST` | `/links/{link_id}/classifications` | classify tables |
| `GET` | `/plan-schema` | supported plan schemas |

## Plans and publishing

| Method | Path | Purpose |
|---|---|---|
| `GET/POST` | `/links/{link_id}/plans` | list plans / run extraction |
| `POST` | `/links/{link_id}/plans/{plan_id}/ignore` | exclude a plan |
| `POST` | `/links/{link_id}/labeling` | run LLM labeling |
| `POST` | `/links/{link_id}/publish` | publish plans to catalog |

Ignore body:

```json
{"ignored": true}
```

## Replay and alerts

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/replay-runs` | list replay runs |
| `POST` | `/replay-runs/create` | enqueue replay work |
| `GET` | `/links/{link_id}/failure` | failure rate and alert state |
| `GET` | `/alerts` | list failure alerts |
| `POST` | `/links/{link_id}/rerun` | requeue a link from a resumable stage |

Replay body:

```json
{"link_ids": [1, 2], "site_id": 1}
```

## Settings and observability

| Method | Path | Purpose |
|---|---|---|
| `GET/PUT` | `/settings` | read/update constance values |
| `GET/PUT` | `/llm-token-budget` | read/set token budget |
| `GET` | `/metrics` | pipeline metrics snapshot |

Settings update body:

```json
{"values": {"REPLAY_PERIOD_HOURS": 12}}
```

Budget body:

```json
{"token_budget": 1000000, "period": "monthly"}
```

Metrics response:

```json
{
  "links_total": 100,
  "links_published": 80,
  "links_awaiting_budget": 2,
  "links_dead_lettered": 1,
  "open_alerts": 0,
  "published_records": 500,
  "llm_tokens_used": 123456
}
```

## Errors

| Code | Status | Meaning |
|---|---|---|
| `not_authenticated` | 401 | no valid token |
| `admin_required` | 403 | caller is not ops/admin |
| `not_found` | 404 | site/link/capture missing |
| `task_backend_unavailable` | 503 | task enqueue failed; transaction rolled back |
