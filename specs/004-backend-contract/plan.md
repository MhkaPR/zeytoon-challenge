# Implementation Plan: Backend Development Contract Compliance

**Branch**: `004-backend-contract` | **Date**: 2026-11-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/004-backend-contract/spec.md`

**Note**: This plan normalizes the existing Django/DRF backend to the rules in
`backend-rules.md`. The project is unpublished, so the plan favors a clean target
structure over backward compatibility with the current code and data.

## Summary

The backend must conform to a single development contract: a predictable project
layout, versioned DRF viewsets with serializer-produced responses, DRF-only request
validation, soft delete and audit logging on every model, immutable migrations,
class-based versioned services, configurable background tasks, structured JSON logging,
and a production WSGI image. The current repository already contains most of the
infrastructure (Django 6, DRF, django-filter, drf-spectacular, django-auditlog,
django-environ, django-constance, django-tasks-db, Redis, PostgreSQL support), but
several modules still violate the contract: hand-built response dictionaries, Pydantic
input schemas in the API layer, a deleted `ActionViewSet` import, non-router URL
configuration, and a test suite built on pytest rather than the mandated Django
`unittest` framework.

The implementation approach is a contract-first normalization in five passes:

1. **Module boundary** — create `apps/pipeline` and move the site, link, capture,
   extraction, classification, plan, replay, alert, and cost-ledger domain out of
   `apps/admin_console`. Remove the `apps/notifications` application entirely. The
   admin console keeps the operator approval and console surface and calls the
   pipeline through its declared interface.
2. **Structure and settings** — finish the `backend/src/apps/<app>` layout, the
   `config/settings/{base,dev,prod}.py` split, versioned view/serializer/service
   directories, and environment-driven configuration.
3. **API boundary** — replace every ad-hoc view with generic DRF viewsets and a
   router, replace every hand-built response with a serializer, and replace every
   Pydantic API input with a DRF serializer.
4. **Data layer** — enforce the shared soft-delete base and manager, register every
   model with django-auditlog, and generate new migrations for schema changes.
5. **Operations and quality** — verify the configurable task backend, JSON logging,
   API schema generation, WSGI production image, and migrate the test suite to Django
   `unittest` with Faker.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Django 6.1, Django REST Framework 3.18, django-filter,
drf-spectacular, django-auditlog, django-environ, django-constance, django-tasks-db,
django-redis, psycopg, gunicorn, django-cors-headers, djangorestframework-simplejwt,
django-guardian

**Storage**: PostgreSQL 16 in production; SQLite is the local development default.
Redis backs the cache and, when selected, the task broker. Artifacts use S3-compatible
object storage or the local filesystem through Django `STORAGES`.

**Testing**: Django `unittest` with Faker, run through `manage.py test`. The current
repository uses pytest/pytest-django; migrating the existing suite to `unittest` is part
of this plan. The migration covers `backend/src/apps/*/tests/` and any
`backend/src/apps/*/tests.py`; the frontend keeps its Vitest suite. Coverage target is
80%, measured outside this contract.

**Target Platform**: Linux server, WSGI (ASGI is not used).

**Project Type**: Web service — Django/DRF modular monolith backend plus a Next.js
frontend in the same repository.

**Performance Goals**: 100 requests per second at peak load with a read-heavy profile;
price changes reflected in search within 5 minutes (constitution VI).

**Constraints**: WSGI only; no repository abstraction over the ORM; no `APIView`; no
Pydantic at the API boundary; every model soft-deleted and audited; migrations are
immutable; the task backend is selected by settings; logs are structured JSON.

**Scale/Scope**: One backend with the `accounts`, `companies`, `catalog`,
`admin_console`, `pipeline`, and shared utility applications (plus supporting internal
modules), three delivered product specs, and one Next.js client. The contract applies
to every current and future application.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| I. Product Domain | Backend features serve search, comparison, or provider ingestion | PASS |
| II. Cost and External Resources | LLM ceiling is model-backed and observable | PASS |
| III. Security and Secrets | Secrets from environment; sensitive data protected | PASS with a documented conflict on the validation mechanism (see Complexity Tracking) |
| IV. Data Governance | Data and services hosted in Iran; Meilisearch local | PASS (deployment concern) |
| V. Architecture | Modular monolith; cross-module access through interfaces | PASS, with an audit task for direct cross-module imports |
| VI. Performance and Scalability | 100 RPS peak; price staleness ≤ 5 minutes | PASS |
| VII. Observability | Structured JSON logs, required metrics, anti-noise | PASS |
| VIII. Quality and Testing | Every behavior has an automated test; regression tests | PASS, with a test-framework migration task |
| IX. Data Retention | Retention rules are explicit and enforced | PASS |
| X. Crawling Ethics | Identifiable crawler, rate limiting | PASS |
| XI. Authentication | JWT-based login | PASS (OTP issues JWT) |
| XII. Established Libraries | Prefer maintained libraries and generators | PASS |
| XIII. Configurable Values | Tunables in settings, constance, or models | PASS |

**Gate result**: PASS with two tracked governance items. The validation-mechanism
conflict is resolved in favor of `backend-rules.md`, which the user mandated after the
constitution was written; the constitution should be amended in a follow-up. The test
framework migration is a delivery task, not a gate failure.

## Project Structure

### Documentation (this feature)

```text
specs/004-backend-contract/
├── plan.md              # This file ($speckit-plan command output)
├── research.md          # Phase 0 output ($speckit-plan command)
├── data-model.md        # Phase 1 output ($speckit-plan command)
├── quickstart.md        # Phase 1 output ($speckit-plan command)
├── contracts/           # Phase 1 output ($speckit-plan command)
└── tasks.md             # Phase 2 output ($speckit-tasks command - NOT created by $speckit-plan)
```

### Source Code (repository root)

```text
Dockerfile                         # production image, built from the project root
backend/
└── src/
    ├── manage.py
    ├── config/
    │   ├── settings/
    │   │   ├── __init__.py        # selects dev by default
    │   │   ├── base.py
    │   │   ├── dev.py
    │   │   └── prod.py
    │   ├── api/
    │   │   ├── urls.py            # /api routes (health)
    │   │   └── v1/
    │   │       └── urls.py        # /api/v1 app routes
    │   ├── urls.py
    │   └── wsgi.py
    └── apps/
        ├── utils/
        │   ├── models/
        │   │   ├── base.py        # TimestampedModel
        │   │   └── soft_delete.py # SoftDeleteManager, DeletedObjectsManager
        │   ├── serializers.py     # shared DRF input helpers
        │   └── apps.py            # auditlog registration
        ├── accounts/
        │   ├── models/
        │   ├── views/v1/
        │   ├── serializers/v1/
        │   ├── services/v1/
        │   ├── tests/
        │   ├── urls.py
        │   ├── admin.py
        │   └── apps.py
        ├── companies/             # same shape
        ├── catalog/               # same shape
        ├── pipeline/              # pipeline domain: models, services/v1, tasks, tests
        │   ├── models/            # Site, Link, CaptureSession, Trace, tables, plans,
        │   │                      # classifications, replays, alerts, cost ledger
        │   ├── services/v1/
        │   ├── tasks.py
        │   ├── interfaces.py
        │   ├── admin.py
        │   └── apps.py
        └── admin_console/         # operator approval + console surface only
            ├── views/v1/
            ├── serializers/v1/
            ├── services/v1/
            ├── tests/
            ├── urls.py
            └── apps.py

frontend/                          # Next.js client; update only where the API contract changes
├── app/
└── src/
```

**Structure Decision**: Use the single repository's existing `backend/src` layout and
normalize each application to the contract shape. `manage.py` stays at
`backend/src/manage.py`, beside `apps/` and `config/`. The project package is
`config`; the application package is `apps`. Version directories exist only under
`views/`, `serializers/`, and `services/`; `models/` and `tests/` are unversioned.
The pipeline application owns the crawl-to-publish domain and its models, services,
tasks, clients, helpers, and constants. The admin console owns the operator approval
queue and operator console endpoints and depends on the pipeline interface.
The Next.js client stays in `frontend/` and is touched only where the response envelope
or endpoint paths change.

The operator console surface is limited to the approval queue, verification decisions,
and the documented operator endpoints. Pipeline constants live in
`apps/pipeline/constants.py`; environment and deployment values stay in settings or
django-constance.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Constitution III and Technology Stack require Pydantic at every external data boundary, while `backend-rules.md` forbids Pydantic at the API boundary | The user explicitly mandated DRF serializers for API input and updated `backend-rules.md`; the contract is newer than the constitution | Keeping Pydantic at the API boundary would violate the explicit user instruction and duplicate validation logic already provided by DRF |
| The current test suite uses pytest/pytest-django, while `backend-rules.md` mandates Django `unittest` | The contract requires one test framework and the user asked for exact compliance | Keeping pytest would leave the repository non-compliant; a dual-framework setup would be harder to maintain |

## Post-Design Constitution Re-check

The Phase 1 artifacts preserve the gate result from the initial check:

- The API contract keeps serializer-first responses and DRF-only input validation, so
  the Pydantic conflict remains the single governance exception and is tracked above.
- The data model requires the shared soft-delete base, audit registration, and immutable
  migrations, satisfying principles III, V, and XIII.
- The quickstart validates structured logging, configurable tasks, WSGI packaging, and
  the test suite, satisfying principles VII, VIII, and XII.
- No new architecture, repository abstraction, microservice, or hard-coded runtime value
  is introduced by the design.

**Re-check result**: PASS with the same two tracked items. No unresolved
`NEEDS CLARIFICATION` markers remain in the plan or research.

## Traceability

| Requirement group | Success criteria |
|---|---|
| Project layout and configuration (FR-001–FR-006) | SC-001, SC-008 |
| API contract (FR-007–FR-018) | SC-002, SC-003, SC-009, SC-013 |
| Authentication and authorization (FR-019–FR-022) | SC-009 |
| Data layer (FR-023–FR-029) | SC-004, SC-005, SC-014 |
| Services and business logic (FR-030–FR-033) | SC-007 |
| Background tasks (FR-034–FR-036) | SC-006 |
| Testing (FR-037–FR-039) | SC-007 |
| Security (FR-040–FR-043) | SC-008 |
| Infrastructure (FR-044–FR-047) | SC-008 |
| Module boundaries (FR-048–FR-052) | SC-011, SC-012 |
| Cross-cutting response rules (FR-053–FR-062) | SC-013, SC-015 |
