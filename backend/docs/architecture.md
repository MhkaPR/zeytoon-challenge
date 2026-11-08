# Backend Architecture

## 1. Purpose and scope

The backend is a **Django 6 + Django REST Framework modular monolith** for a Persian-first
host/server plan comparison platform. It owns:

- phone-based SMS OTP authentication and JWT sessions;
- company registration, operator verification, credit, and the company panel;
- an automated crawl → extract → label → publish pipeline for provider plan pages;
- a read-only public catalog of published plans;
- a per-viewer recommendation/ranking service;
- an operator console for approvals, pipeline operations, settings, and metrics.

The frontend is a separate Next.js application. The backend exposes JSON under
`/api/v1/`, OpenAPI under `/api/schema/`, Swagger UI under `/api/docs/`, and Django admin
under `/admin/`.

## 2. System context

```text
Next.js frontend
      │  HTTPS /api/v1
      ▼
Django + DRF (WSGI)
      ├── PostgreSQL      source of truth
      ├── Redis           cache, OTP TTL, throttles, recommendation space cache
      ├── Object storage  domtrack traces (S3-compatible or filesystem)
      ├── crawl4ai        adaptive link discovery (server-side)
      ├── domtrack        headless capture, table extraction, replay/diff
      └── OpenAI-compatible LLM provider
```

All services are expected to run in-country. PostgreSQL is the production source of
truth; SQLite is a local-development convenience only.

## 3. Repository layout

```text
backend/
├── docs/                       this documentation
└── src/
    ├── manage.py
    ├── config/
    │   ├── settings/           base.py, dev.py, test.py, prod.py
    │   ├── api/                /api routing, health, v1 aggregation
    │   ├── urls.py             root URLconf
    │   └── wsgi.py
    └── apps/
        ├── utils/              shared base models, soft delete, logging, pagination
        ├── accounts/           users, roles, OTP, JWT, SMS, throttling
        ├── companies/          registration, verification, panel, credit
        ├── catalog/            published plan read model and public API
        ├── pipeline/           discovery, capture, extraction, publishing, replay
        ├── admin_console/      operator-only API over companies + pipeline
        ├── recommendations/    interest profiles, plan space, ranking
        ├── core/               public site configuration helpers
        ├── analytics/          scaffold only
        └── normalizer/         scaffold only
```

`apps.analytics`, `apps.normalizer`, and `apps.core` are **not** listed in
`INSTALLED_APPS`. `core` is still imported as a plain module for site configuration;
`analytics` and `normalizer` are placeholders with no registered behavior.

## 4. Layering and dependency rules

Each domain app follows the same internal shape:

```text
views/v1/        HTTP boundary: resolve caller, validate input, call services/selectors
serializers/v1/  DRF input validation and response shaping
services/v1/     write-side business logic and transactions
selectors.py     read-side queries and projections
models/          Django models (one module per cohesive model group)
interfaces.py    the only sanctioned entry point for other apps
tasks.py         Django Tasks task bodies
events.py        structured domain-event logging
```

Rules enforced by the codebase:

- Views call services/selectors; business rules do not live in views.
- API input is validated by DRF serializers, never Pydantic. Pydantic is used only for
  LLM structured output inside `pipeline`.
- Cross-app access goes through the owning app's `interfaces.py`. Other apps must not
  query another app's tables directly.
- The ORM is used directly; there is no repository abstraction.
- All models inherit `apps.utils.models.TimestampedModel`, which provides timestamps and
  soft delete.
- Background work uses Django Tasks (`django.tasks`), not Celery.
- Runtime-tunable values live in django-constance, not hard-coded constants.

### Cross-app interfaces

| Interface | Owns | Used by |
|---|---|---|
| `AccountsInterface` | identity resolution, OTP, token revocation, return URLs | views, other apps needing identity |
| `CompaniesInterface` | company reads, step progress, verification decisions | `admin_console`, `pipeline` |
| `CatalogInterface` | published-record upsert/retire/read | `pipeline`, `recommendations` |
| `PipelineInterface` | sites, links, captures, task enqueue, public site/link data | `admin_console`, `catalog`, `companies` |
| `RecommendationsInterface` | ranking, signal recording, visitor merge/clear | `catalog`, `accounts` |

## 5. Routing

```text
/api/health/                     health check
/api/v1/auth/...                 accounts
/api/v1/companies/...            companies
/api/v1/catalog/...              catalog
/api/v1/recommendations/...      recommendations
/api/v1/ops/...                  admin_console
/api/schema/                     OpenAPI schema
/api/docs/                       Swagger UI
/admin/                          Django admin
```

Version aggregation lives in `config/api/v1/urls.py`. Each app owns its router and
`urls.py`.

## 6. Authentication and authorization

- Authentication is **phone number + SMS OTP** only.
- Access tokens are short-lived JWTs (`15` minutes by default). Refresh tokens rotate and
  are stored in an `httpOnly`, `SameSite=Strict` cookie scoped to `/api/v1/auth/`.
- Refresh rotation blacklists the previous token (`rest_framework_simplejwt.token_blacklist`).
- Roles are Django groups: `regular`, `ops`, `admin`. `admin` wins over `ops`, which wins
  over `regular`; a Django superuser is always `admin`.
- `ops` users can use `/api/v1/ops/`; `admin` users additionally have Django-admin access.
- Object-level permissions use django-guardian.
- Company-scoped endpoints resolve the caller from the Bearer token and scope every query
  to companies the caller owns.

## 7. Persistence and data conventions

- PostgreSQL in production, SQLite locally; configured through `DATABASE_URL`.
- `AUTH_USER_MODEL = accounts.User`.
- Every model inherits `TimestampedModel`:
  - `created_at`, `updated_at`, `deleted_at`;
  - `objects` returns active rows only;
  - `deleted_objects` returns soft-deleted rows;
  - `delete()` soft-deletes and raises `SoftDeleteConflict` when a required relation still
    references the row;
  - `hard_delete()` is the explicit physical delete.
- Audit logging is registered for project models in `apps.utils.apps.UtilsConfig.ready()`.
- Append-only records (`VerificationDecision`, `CreditLedgerEntry`) override `save()` and
  `delete()` to reject mutation.
- Unique constraints generally include `deleted_at__isnull=True` so a soft-deleted row
  does not block a new active row.

## 8. Configuration

- Secrets and environment-specific values: environment variables via `django-environ`.
- Runtime-tunable values: django-constance, editable from Django admin or the operator
  settings endpoint.
- Settings modules:
  - `config.settings.base` — shared defaults;
  - `config.settings.dev` — local development;
  - `config.settings.test` — in-memory cache and constance backend for pytest;
  - `config.settings.prod` — secure cookies and production defaults.

## 9. Background work and storage

- Django Tasks with the database backend (`django_tasks_db`) is configured in `TASKS`.
- Pipeline work is enqueued per site/link and resumed from the persisted link stage.
- `recover_site_pipeline_tasks` requeues interrupted work and closes stale capture
  sessions.
- Traces and artifacts are written through Django `STORAGES`; the backend is selected by
  `ARTIFACT_STORAGE_BACKEND` (`s3` or filesystem).

## 10. Observability

- Logging is structured JSON via `apps.utils.logging`.
- A logging filter redacts OTP codes and tokens from messages and arguments.
- Domain events are emitted with an `event` field by each app's `events.py`.
- Health endpoint: `GET /api/health/`.
- Operator metrics: `GET /api/v1/ops/metrics`.

## 11. API conventions

- ViewSets only (`GenericViewSet` with mixins or `@action`); no `APIView`.
- JSON fields are `snake_case`.
- Paginated list responses: `{"data": [...], "page": {...}}`.
- Detail/POST/PUT/PATCH responses: `{"data": {...}}` where the app uses the envelope.
- Errors share one shape:

```json
{
  "error": {
    "code": "invalid_field",
    "message": "Some fields are missing or invalid.",
    "fields": {"fields": ["domain"]}
  }
}
```

- Throttling is configured in `REST_FRAMEWORK.DEFAULT_THROTTLE_RATES`; OTP and
  recommendation endpoints add scoped throttle classes.

## 12. App catalog

| App | Responsibility | Status |
|---|---|---|
| `accounts` | users, roles, OTP, JWT, SMS, throttling | implemented |
| `companies` | registration, verification, panel, credit, crawl toggle | implemented |
| `catalog` | published plan read model and public browsing API | implemented |
| `pipeline` | discovery, capture, extraction, labeling, publishing, replay | implemented |
| `admin_console` | operator approval and pipeline console | implemented |
| `recommendations` | interest profiles and related-plan ranking | implemented |
| `core` | public site configuration helpers | implemented (module) |
| `utils` | shared model, logging, pagination, serializer helpers | implemented |
| `analytics` | planned metrics/analytics | scaffold |
| `normalizer` | planned provider-data normalization | scaffold |
