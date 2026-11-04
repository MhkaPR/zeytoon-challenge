# Backend Development Contract

## 1. Stack & Versions

| Component | Version / Choice |
|---|---|
| Python | 3.14 |
| Django | 6.0 (released 2025-12-03) |
| PostgreSQL | 16 |
| Redis | Used as cache and task queue broker |
| Dependency management | `uv` |
| Linting | `black`, `flake8` |
| Type hints | **Optional** — not required |
| WSGI | Yes (ASGI not used) |
| Dockerfile | Production build only (dev uses `manage.py runserver`) |

## 2. Project Layout

```
project-root/
├── manage.py
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   └── api/
│       ├── urls.py              # routes /api
│       └── v1/
│           └── urls.py          # routes v1 app URLs
├── apps/
│   ├── utils/                   # shared utilities only (incl. soft-delete manager)
│   └── <app>/
│       ├── models/
│       ├── views/
│       │   └── v1/              # DRF viewsets
│       ├── serializers/
│       │   └── v1/
│       ├── services/
│       │   └── v1/
│       ├── tests/
│       ├── admin.py
│       ├── tasks.py
│       └── apps.py
└── Dockerfile
```

- `manage.py` sits beside `apps/`, not inside it.
- `config` is the Django project package (contains `admin` config, root URLconf).
- `settings.py` in `config/settings/` selects the environment file: `base.py` is imported by `dev.py`/`prod.py`.
- Version directories exist in `views/`, `serializers/`, and `services/`. `models/` and `tests/` are not versioned.
- The `models/` directory holds one model module per model (or cohesive model group); its `__init__.py` only re-exports, it MUST NOT define models.

## 3. Settings & Configuration

- Environment variables are read via **django-environ**.
- A `.env` file lives in the project root (not committed). A `.env.dist` template is committed.
- `SECRET_KEY`, `DEBUG`, `DATABASE_URL`, `REDIS_URL` are read from environment.
- Logging is **JSON** format. Default log level is `INFO`.
- API documentation via **drf-spectacular** is mandatory.

## 4. Authentication & Authorization

- Authentication is handled by the pre-built `accounts` Django app. That app owns the custom user model, OTP logic, and token issuance.
- Login identifier: **phone number only**. Email/username login is not supported.
- **OTP is the default** authentication flow. Any deviation requires explicit approval.
- Authorization uses **default permission classes** defined per project. Custom permission classes live in the relevant app’s `permissions.py` or `views/v1/` scope.

## 5. API Conventions

- Base URL pattern: `/api/<version>/`. Version routing lives in `config/api/<version>/urls.py`.
- **ViewSets only** — `APIView` is not used.
- Use real DRF generic viewsets: `ModelViewSet`, `GenericViewSet` with mixins, and `@action` for extra endpoints. A bare `ViewSet` is only acceptable when no generic viewset or mixin applies. Custom `as_view` overrides that reimplement routing are forbidden.
- **Serializers are versioned** under `serializers/v1/`, `serializers/v2/`, etc.
- **Every API response body is produced by a serializer**, never by a hand-built `dict`. Use `ModelSerializer` for model instances and `Serializer`/`BaseSerializer` for class-based, computed, or aggregate payloads; views call `serializer.data` (or `serializer(instance).data`) instead of assembling dictionaries inline.
- **API input is validated by DRF serializers, never by Pydantic.** At the API boundary the request body is passed to a `Serializer`/`ModelSerializer`; `Pydantic` is not imported in any `api`/`serializers` module. (Pydantic stays internal to non-API tooling such as LLM structured output.)
- **Response envelope**:
  - List responses: `{"data": [...], "page": {...}}`
  - Detail / POST / PUT / PATCH responses: `{"data": {...}}`
- **JSON field naming**: `snake_case`, mandatory.
- Filtering, search, and ordering: **django-filter**.
- Pagination: default page size only (no other pagination schemes unless explicitly requested).
- CORS: handled by the standard CORS library.
- Throttling: handled by the standard throttling library.
- Health check endpoint: `/api/health/` (outside versioned routes).

## 6. Data Layer

- **No repository pattern.** Django ORM is used directly. ORM must not be wrapped in a repository abstraction.
- **Soft delete is mandatory on all models.** Implementation is **not** delegated to a third-party library.
  - A custom **manager class is written in `apps/utils/`** and used by every model.
  - All models inherit from a shared base model in `apps/utils/` that exposes:
    - `objects` — returns non-deleted records.
    - `deleted_objects` (or equivalent) — returns deleted records.
    - `delete()` — performs soft delete (sets a `deleted_at` / `is_deleted` flag).
    - `hard_delete()` — performs physical deletion when explicitly required.
  - This is the **only permitted implementation** of soft delete. Hand-written per-model managers, inline flag checks in queries, or third-party soft-delete libraries are prohibited.
- **Audit logging**: **django-auditlog** is mandatory on all models.
  - Register models via `auditlog.register(ModelName)` at the bottom of `models.py`.
  - `AuditlogMiddleware` is enabled so the actor is captured automatically.
- **Migrations are never edited by hand.** Every database change gets a new migration file. Existing migration files are immutable.
- Database table names: the Django default (no `db_table` prefix) unless a specific exception is approved.

## 7. Services & Business Logic

- **OOP first**: business logic lives in classes, not loose functions. This applies to services, models, and viewsets.
- **Library first → SOLID → DRY** (in that priority order).
- **Backward compatibility of services is mandatory.**
  - If a service contract cannot remain backward compatible, a **new service** is written alongside the old one; the old service is left untouched.
  - Service versioning follows the same `services/v1/`, `services/v2/` pattern.
- If a change requires an incompatible service signature, the new version lives in a new version directory; the old version remains for existing callers.

## 8. Background Tasks (Django Tasks Framework)

- Background work uses **Django’s built-in Tasks framework** (Django 6.0+).
- Task functions are defined in `apps/<app>/tasks.py` with `from django.tasks import task`.
- The **task backend is not hard-coded**; it is configured in settings via the `TASKS` dictionary:
  ```python
  TASKS = {
      "default": {
          "BACKEND": "django_tasks.backends.rq.RQBackend",  # example
          "QUEUES": ["default"],
      }
  }
  ```
- **Backend selection is an infrastructure decision** made per server. The codebase must not assume a specific backend.
- Supported backends include:
  - `django_tasks.backends.database.DatabaseBackend` (requires `django_tasks.backends.database` in `INSTALLED_APPS`)
  - `django_tasks.backends.rq.RQBackend` (Redis/RQ)
  - Third-party backends (e.g., Celery via `django-tasks-fennel`) are permitted if the server requires them.
- Tasks are enqueued with `.enqueue()`, not called directly.

## 9. Testing

- Framework: **Django `unittest`**.
- **Faker** is used for test data.
- **Coverage ≥ 80%** is the target. Measurement and enforcement are the responsibility of the DevOps team and are **not** part of this document.
- **Regression tests are mandatory for every change** that alters behavior.
- Test files live under `apps/<app>/tests/`. Version-specific view/service tests live under `tests/v1/`, `tests/v2/`, etc.

## 10. Security

- **Passwords and OTPs are hashed.** Phone numbers are stored as-is (no hashing required).
- **OTP abuse protection** (rate limiting on OTP request and verification endpoints) is handled by the pre-built `accounts` app.
- **Payment gateway integration** uses the organization’s dedicated payment library. That library covers the payment operation only; wallet and domain-specific payment logic stay in the project’s services layer.
- **Payment webhooks** are managed by the dedicated payment library.
- **CORS and CSRF** are configured via the standard libraries. CSRF is disabled for token-based API endpoints.
- **Secrets** are never committed. `.env` is excluded from version control; `.env.dist` documents required variables.

## 11. Infrastructure

- **WSGI** is the deployment interface. ASGI is not used.
- **Dockerfile is for production only.** It builds the production image from the project root. Development runs via `python manage.py runserver` directly.
- **No CI pipeline** is required by this document. The DevOps team handles test coverage measurement and any pipeline concerns outside this contract.
- **No pre-commit hooks** are required.
- **Redis** is used as the cache backend and as the broker for the task backend (when RQ or a Redis-backed backend is selected).

## 12. Enforcement

The following rules are **gates** — deviations are not permitted without explicit approval:

1. No repository abstraction over Django ORM.
2. No hand-editing of migration files.
3. No `APIView` — ViewSets only.
4. No email/username login — phone number only.
5. No repository pattern; services are class-based.
6. Soft delete is mandatory on every model via a **custom manager class in `apps/utils/`**; third-party soft-delete libraries are prohibited.
7. Audit logging is mandatory via `django-auditlog`.
8. JSON `snake_case` in API payloads is mandatory.
9. Response envelope (`data` + optional `page`) is mandatory.
10. Django Tasks framework is the only background-task mechanism; backend is infrastructure-configured.
11. API versioning only for major breaking changes.
12. `drf-spectacular` documentation is mandatory.
13. Production Dockerfile must exist at the project root.

Any proposed architecture not described in this document is **gated** and must be rejected at review time.
