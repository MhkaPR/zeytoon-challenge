# admin_console — Architecture

## 1. Responsibility

`apps.admin_console` is the **operator-only API** over company verification and the
automated pipeline. It has **no domain models**; all state lives in `companies` and
`pipeline`.

It provides:

- the company approval queue and verification decisions;
- site onboarding, suspension, and link discovery;
- capture, extraction, classification, labeling, plan, and publish controls;
- replay scheduling and inspection;
- failure alerts and link rerun;
- runtime settings, LLM token budget, and metrics.

## 2. Internal layout

| Path | Responsibility |
|---|---|
| `views/v1/admin_console.py` | `OpsViewSet` with all operator actions |
| `serializers/v1/admin_console.py` | input/output serializers |
| `services/v1/admin_console.py` | approval queue and decision orchestration |
| `urls.py` | `/api/v1/ops/` routes |
| `models/__init__.py` | intentionally empty |

## 3. Authorization

`OperatorViewSet.caller()`:

1. resolves the Bearer user through `apps.accounts.selectors`;
2. rejects missing identity with `401 not_authenticated`;
3. rejects non-operators with `403 admin_required`.

`User.is_operator()` is true for `ops` and `admin` roles.

## 4. Orchestration boundary

The console never writes another app's tables directly. It calls:

- `CompaniesInterface` for approval queue, company lookup, and verification decisions;
- `PipelineInterface` for site/link/capture lookups, onboarding, suspension, resume, and
  task enqueue;
- `pipeline.services.v1.pipeline` for stage operations and metrics;
- `apps.core.site_config` for the settings snapshot.

This keeps the console a thin composition layer.

## 5. Approval orchestration

`services.record_decision()`:

```text
company = CompaniesInterface.company_or_error(company_id)
decision = CompaniesInterface.record_verification_decision(...)
site = PipelineInterface.site_for_company(company.pk)

approved:
  if no site: onboard_site
  elif suspended: resume_site
  enqueue_site_pipeline

not_approved:
  if site: suspend_site
```

The whole operation runs in one transaction.

## 6. Task backend failures

If enqueueing fails, the console raises `TaskBackendUnavailable` and rolls back the
transaction, so a decision that cannot be scheduled is not partially applied.

## 7. Dependencies

- `apps.accounts` for identity and `ApiError`.
- `apps.companies` via `CompaniesInterface`.
- `apps.pipeline` via `PipelineInterface` and pipeline services.
- `apps.core` for frontend settings snapshot.
- `django-constance` for runtime settings updates.
