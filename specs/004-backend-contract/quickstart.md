# Quickstart Validation: Backend Development Contract Compliance

**Feature**: `004-backend-contract`
**Date**: 2026-11-05

This guide proves that the backend conforms to `backend-rules.md`. It describes how to
run and validate the contract; implementation details belong in `tasks.md`.

## Prerequisites

- Python 3.14 available.
- `uv` installed.
- Repository checked out at the project root.
- A local `.env` created from `.env.dist` for development.
- Redis available if the selected task/cache backend requires it.
- PostgreSQL available for a production-like run; SQLite is acceptable for local
  development.

## Setup

```bash
uv sync
cp .env.dist .env
```

Set at minimum:

```text
DJANGO_SECRET_KEY=...
DJANGO_DEBUG=true
DATABASE_URL=sqlite:///backend/src/db.sqlite3
REDIS_URL=redis://localhost:6379/0
```

## 1. Start the development service

```bash
cd backend/src
python manage.py migrate
python manage.py runserver
```

**Expected**: The service starts with development settings, applies migrations, and
serves the API on the development port.

## 2. Verify the API schema

Open:

- `http://localhost:8000/api/schema/`
- `http://localhost:8000/api/docs/`

**Expected**: The schema lists the versioned endpoints and their request/response
serializers. See [contracts/api-conventions.md](./contracts/api-conventions.md).

## 3. Verify the response envelope and validation

Call a collection endpoint and a detail endpoint.

**Expected**:

- Collection: `{"data": [...], "page": {...}}`.
- Detail or mutation: `{"data": {...}}`.
- Field names are snake_case.
- Invalid input returns the shared error shape.

## 4. Verify soft delete

In a Django shell:

```bash
cd backend/src
python manage.py shell
```

Create a record, soft-delete it, and query it through the default and deleted-record
managers.

**Expected**:

- The default manager excludes the record.
- The deleted-record manager includes it.
- `hard_delete()` removes it physically.

See [data-model.md](./data-model.md) for the shared base and manager contract.

## 5. Verify audit logging

Create or update a model instance, then inspect the audit log.

**Expected**: An audit entry exists for the change, with the actor when a request user
is available.

## 6. Verify migrations

```bash
cd backend/src
python manage.py makemigrations --check --dry-run
```

**Expected**: No pending model changes. If a model changed, a new migration file exists
and no existing migration was edited.

## 7. Verify background tasks

Inspect the `TASKS` setting and enqueue a task through the configured backend.

**Expected**:

- The task is defined with the framework decorator in the owning application.
- The backend comes from settings.
- The task is dispatched with `.enqueue()`.

## 8. Verify structured logging

Trigger a request or task and inspect the console output.

**Expected**: Each log line is valid JSON at `INFO` or the configured level, and
sensitive values are masked.

## 9. Run the backend test suite

```bash
cd backend/src
pytest
```

**Expected**: The suite passes using pytest and Faker test data. Every
behavior change in the release has a regression test.

## 10. Build the production image

```bash
docker build -f Dockerfile -t torob-backend .
```

**Expected**: The image builds from the project root and starts the service with
Gunicorn over WSGI.

## 11. Verify the pipeline boundary

Inspect the application packages.

**Expected**:

- `apps/pipeline/` owns the site, link, capture, trace, table, classification, plan,
  replay, alert, and cost-ledger models, plus the stage services, tasks, clients, and
  helpers.
- `apps/admin_console/` contains only the operator approval and console surface and
  imports pipeline behavior through the pipeline interface.
- `apps/notifications/` does not exist, and no settings, URL, service, or test
  references it.

## Contract Gate Review

Before merging, confirm:

- [ ] Layout matches the contract.
- [ ] Every endpoint is a generic viewset action.
- [ ] Every response is serializer-produced.
- [ ] Every request is serializer-validated.
- [ ] No Pydantic at the API boundary.
- [ ] Every model is soft-deleted and audited.
- [ ] Migrations are new files only.
- [ ] Services are class-based and versioned.
- [ ] Tasks are framework-defined and enqueued.
- [ ] JSON logs are structured.
- [ ] The schema is generated.
- [ ] The production image builds.
- [ ] The pipeline application owns all pipeline domain code.
- [ ] The admin console owns no pipeline model or stage service.
- [ ] The notifications application is removed.
