# Phase 0 Research: Backend Development Contract Compliance

**Feature**: `004-backend-contract`
**Date**: 2026-11-05
**Source of truth**: `backend-rules.md`

This research resolves the technical choices needed to implement the contract. The
project is unpublished, so decisions favor a clean target state over preserving the
current code and database.

## Decision 1 — Project layout

**Decision**: Keep `backend/src/manage.py`, `backend/src/config/`, and
`backend/src/apps/`. Normalize every application to `models/`, `views/v1/`,
`serializers/v1/`, `services/v1/`, and `tests/`. Keep `models/__init__.py` as a
re-export-only module.

**Rationale**: The repository already uses this layout after the in-progress refactor.
The contract's tree matches it once the remaining loose modules are moved. Keeping the
entry point beside `apps/` and `config/` satisfies the contract without changing the
working command paths.

**Alternatives considered**:

- Move `manage.py` to the repository root. Rejected because the contract places it
  beside `apps/`, and the current `backend/src` layout is the established project
  boundary.
- Keep loose modules at the application root. Rejected because the contract requires
  versioned view/serializer/service directories and model modules.

## Decision 2 — Settings and environment

**Decision**: Keep `config/settings/{base,dev,prod}.py`, with `config/settings/__init__.py`
selecting development settings for local commands. Read secrets and environment-specific
values through `django-environ`. Keep runtime tunables in `django-constance`.

**Rationale**: This is already implemented and matches the contract. It also satisfies
constitution XIII: environment values live in settings, operator-tunable values live in
the database.

**Alternatives considered**:

- A single `settings.py` with conditionals. Rejected because the contract requires
  separate base/dev/prod files.
- Hard-coded defaults for secrets. Rejected by the security rules.

## Decision 3 — API implementation style

**Decision**: Use DRF `ModelViewSet`, `GenericViewSet` with mixins, and `@action` for
custom endpoints. Mount application viewsets with a DRF router. Do not use `APIView`.
Do not override `as_view` to reimplement routing.

**Rationale**: The contract explicitly requires generic viewsets and forbids custom
routing overrides. A router gives consistent URL naming and schema generation.

**Alternatives considered**:

- A custom `ActionViewSet` that maps HTTP verbs to same-named methods. Rejected: it
  reimplements routing and was explicitly rejected by the user.
- `APIView` per endpoint. Rejected by the contract.
- Function-based views. Rejected by the contract.

## Decision 4 — Response construction

**Decision**: Every response body is produced by a serializer. Use `ModelSerializer`
for model instances and `Serializer`/`BaseSerializer` for computed or aggregate
payloads. Views call `serializer.data`; they do not assemble response dictionaries.

**Rationale**: The contract makes serializer-produced responses a gate. It also keeps
the OpenAPI schema accurate and prevents response drift.

**Alternatives considered**:

- Hand-built dictionaries in views. Rejected by the contract.
- Returning model `.values()` dictionaries. Rejected because they bypass serializers
  and field documentation.

## Decision 5 — Request validation

**Decision**: Validate every request body with a DRF serializer. Do not import Pydantic
in API or serializer modules. Keep Pydantic only for internal, non-API structured
output such as LLM extraction.

**Rationale**: This is the user's explicit correction and the current contract. DRF
already provides validation, error shaping, and schema generation at the API boundary.

**Alternatives considered**:

- Pydantic schemas at the API boundary. Rejected by the contract and by explicit user
  instruction.
- Manual `request.data` checks. Rejected because they bypass DRF validation and error
  handling.

## Decision 6 — Response envelope

**Decision**: Collection responses use `{"data": [...], "page": {...}}`; detail and
mutation responses use `{"data": {...}}`. Field names are snake_case.

**Rationale**: The contract makes this envelope mandatory. The frontend client must be
updated wherever it currently reads `results` or a top-level object.

**Alternatives considered**:

- Keep the existing `results` key. Rejected because it violates the contract.
- Return bare arrays. Rejected because it prevents pagination metadata and breaks the
  envelope rule.

## Decision 7 — Filtering and pagination

**Decision**: Use `django-filter` through DRF's `DjangoFilterBackend`, with
`SearchFilter` and `OrderingFilter` where needed. Set a default page-size pagination
class in `REST_FRAMEWORK`.

**Rationale**: The contract requires django-filter and default page-size pagination.
Central settings keep every viewset consistent.

**Alternatives considered**:

- Per-view manual `request.query_params` filtering. Rejected because it duplicates
  django-filter and is hard to document.
- Cursor or limit-offset pagination. Rejected unless explicitly requested.

## Decision 8 — Soft delete

**Decision**: Use the shared `TimestampedModel` and `SoftDeleteManager` in
`apps/utils/models/`. Every domain model inherits the base. `objects` excludes deleted
records, `deleted_objects` includes them, `delete()` soft-deletes, and `hard_delete()`
physically deletes.

**Rationale**: The contract requires one shared implementation and forbids third-party
soft-delete libraries and per-model flag checks.

**Alternatives considered**:

- `django-soft-delete` or similar. Rejected by the contract.
- A boolean flag checked in every query. Rejected because it is error-prone and
  explicitly prohibited.

## Decision 9 — Audit logging

**Decision**: Register every domain model with `django-auditlog` and enable
`AuditlogMiddleware`. Registration lives in the shared utilities application's
`ready()` hook so new models are covered automatically.

**Rationale**: The contract requires audit logging on all models and actor capture.
Central registration avoids per-app omissions.

**Alternatives considered**:

- Per-model `auditlog.register` calls scattered across apps. Rejected because it is
  easy to forget and duplicates the same boilerplate.
- A custom audit table. Rejected because the contract mandates `django-auditlog`.

## Decision 10 — Migrations

**Decision**: Generate new migrations for every schema change with
`manage.py makemigrations`. Never edit an existing migration file. Verify with
`makemigrations --check --dry-run`.

**Rationale**: The contract makes migration immutability a gate. The project is
unpublished, so new migrations may replace the current schema history only through
normal generation, not hand editing.

**Alternatives considered**:

- Squash or rewrite migrations by hand. Rejected by the contract.
- `--fake` migrations to hide drift. Rejected because it leaves the schema and history
  inconsistent.

## Decision 11 — Background tasks

**Decision**: Define tasks with `from django.tasks import task` in each application's
`tasks.py`, and enqueue them with `.enqueue()`. Keep the backend in the `TASKS` setting
so infrastructure can choose the implementation.

**Rationale**: The contract mandates Django's task framework and forbids hard-coding a
backend. The repository already uses `django_tasks_db.DatabaseBackend` through
settings.

**Alternatives considered**:

- Celery. Rejected by the contract unless a server explicitly selects a third-party
  backend.
- Calling task functions directly. Rejected because it bypasses retries and workers.

## Decision 12 — Testing framework

**Decision**: Migrate the backend test suite to Django `unittest` classes and use
Faker for test data. Run tests with `manage.py test`. Keep pytest only as an optional
local convenience if it does not become the contract's official runner.

**Rationale**: The contract names Django `unittest` as the framework. The current suite
uses pytest-style functions, so this is a mechanical migration rather than a behavioral
rewrite.

**Alternatives considered**:

- Keep pytest. Rejected because the contract is explicit.
- Run both frameworks indefinitely. Rejected because it doubles test infrastructure and
  obscures the official command.

## Decision 13 — API documentation

**Decision**: Keep `drf-spectacular` with `DEFAULT_SCHEMA_CLASS` and expose the schema
and Swagger routes at `/api/schema/` and `/api/docs/`.

**Rationale**: The contract makes documentation mandatory. The repository already has
the package and routes.

**Alternatives considered**:

- Hand-written OpenAPI files. Rejected because they drift from the code.
- No documentation. Rejected by the contract.

## Decision 14 — Logging

**Decision**: Keep the JSON formatter and sensitive-data filter in
`apps/utils/logging.py`. Default level is `INFO`, configurable through `LOG_LEVEL`.

**Rationale**: The contract requires structured JSON logs. The existing implementation
already satisfies it and masks OTPs and tokens.

**Alternatives considered**:

- Plain text logs. Rejected by the contract.
- Per-request debug logging in hot loops. Rejected by the anti-noise principle.

## Decision 15 — Production packaging

**Decision**: Keep a production Dockerfile at the project root and run the service with
Gunicorn over WSGI. Development uses `manage.py runserver`.

**Rationale**: The contract requires a root production Dockerfile and WSGI. The current
Dockerfile lives under `backend/`, so it must move or be duplicated at the root with the
backend path as its build context.

**Alternatives considered**:

- ASGI with Uvicorn. Rejected by the contract.
- A development Dockerfile. Rejected because the contract limits Docker to production.

## Decision 16 — Authorization

**Decision**: Replace ad-hoc role checks with DRF permission classes backed by Django
groups and django-guardian. Keep public endpoints explicitly `AllowAny`; set a safe
authenticated default for the rest.

**Rationale**: The constitution forbids ad-hoc boolean role flags and requires
django-guardian for object-level permissions. The current `AllowAny` default is too
permissive for an operator console.

**Alternatives considered**:

- Keep `AllowAny` globally and check roles inside views. Rejected because it is easy to
  forget and violates the authorization principle.
- Use a custom boolean flag on the user model. Rejected by the constitution.

## Decision 17 — Pipeline application boundary

**Decision**: Create `apps/pipeline` and move the crawl-to-publish domain out of
`apps/admin_console`. The pipeline application owns the site, link, capture, trace,
table, classification, plan, replay, alert, and LLM cost-ledger models, plus the stage
services, tasks, discovery client, domtrack client, artifact helper, event emitters,
LLM helper, plan schema, replay engine, table classifier, and pipeline constants. The
admin console keeps the operator approval queue and console endpoints and calls the
pipeline through a declared interface. The notifications application is removed
entirely.

**Rationale**: The pipeline is the largest and most change-prone domain. Separating it
from operator presentation makes both sides independently testable and gives the
pipeline a stable interface for the console and future consumers. It also removes the
current mixing of pipeline models and stage logic inside the admin console.

**Alternatives considered**:

- Keep the pipeline inside `admin_console` and only rename the module. Rejected because
  it preserves the mixed responsibilities the user asked to separate.
- Split each pipeline stage into its own application. Rejected because the stages share
  models and transaction boundaries; one pipeline application keeps the domain cohesive.
- Keep the notifications application and disable its routes. Rejected because the user
  asked for complete removal.

## Resolved unknowns

No `NEEDS CLARIFICATION` markers remain. The only governance conflict is the
Pydantic-versus-DRF validation rule, which is resolved in favor of the user-mandated
`backend-rules.md` and recorded in the plan's Complexity Tracking table.
