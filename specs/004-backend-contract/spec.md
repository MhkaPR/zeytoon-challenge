# Feature Specification: Backend Development Contract Compliance

**Feature Branch**: `004-backend-contract`

**Created**: 2026-11-05

**Status**: Draft

**Input**: User description: "read the backend-rules.md and write a spec for that for more precise work"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Predictable project structure and environment (Priority: P1)

A developer or agent opens the repository and can locate every backend concern without guessing: the project entry point, environment settings, versioned API routes, and each application's models, views, serializers, services, and tests. A fresh checkout starts in a documented development environment, and the same code runs in production with production settings selected by the environment.

**Why this priority**: Every other rule depends on a predictable layout. Without it, refactors, reviews, and automated work produce inconsistent results.

**Independent Test**: Starting from a clean checkout, a developer can identify the entry point, the development and production settings, the versioned route files, and the model/view/serializer/service/test locations for any application, then start the development server using only the documented commands.

**Acceptance Scenarios**:

1. **Given** a clean checkout, **When** a developer inspects the backend root, **Then** the management entry point sits beside the applications package and the project configuration package, with environment settings separated into a base file and development/production files.
2. **Given** an application, **When** a developer inspects it, **Then** models, versioned views, versioned serializers, versioned services, and tests occupy the documented locations, and the models package contains one module per model or cohesive model group.
3. **Given** the models package initializer, **When** a developer reads it, **Then** it only re-exports model classes and defines no model class itself.
4. **Given** an environment with the documented variables set, **When** the service starts in development or production mode, **Then** it reads secrets, database, cache, and queue configuration from the environment rather than from committed files.

---

### User Story 2 - Consistent, documented API behavior (Priority: P1)

An API consumer calls any versioned endpoint and receives a predictable contract: the same URL versioning scheme, the same response envelope, snake_case field names, documented schemas, and validation errors produced by the same request-validation mechanism. Operators can browse the generated API documentation and trust that it reflects the running endpoints.

**Why this priority**: The frontend and external consumers integrate against these endpoints. Inconsistent response shapes or validation paths break clients and make the API unsafe to evolve.

**Independent Test**: Call a list endpoint and a detail endpoint, confirm the documented envelope and snake_case fields, submit invalid input and confirm a structured validation error, then open the generated schema and confirm both endpoints and their payloads are described.

**Acceptance Scenarios**:

1. **Given** a versioned API route, **When** a client requests a collection, **Then** the response contains a `data` collection and an optional `page` object.
2. **Given** a versioned API route, **When** a client requests a detail or submits a create/update request, **Then** the response contains a `data` object.
3. **Given** any endpoint, **When** a client submits a request body, **Then** the body is validated by a DRF serializer and invalid input returns a structured error rather than reaching business logic.
4. **Given** any endpoint, **When** a client reads the response, **Then** every field name is snake_case and the response body was produced by a serializer.
5. **Given** the running service, **When** a developer opens the API documentation route, **Then** the generated schema lists the versioned endpoints and their request/response shapes.
6. **Given** a collection endpoint, **When** a client filters, searches, or orders results, **Then** those capabilities are provided by the standard filtering library and default page-size pagination.

---

### User Story 3 - Safe data lifecycle and change history (Priority: P1)

A data steward deletes a record and expects it to disappear from normal reads while remaining recoverable, with a full audit trail of who changed what and when. A developer changes a model and expects a new migration rather than an edited historical migration, so deployed databases and fresh databases converge on the same schema.

**Why this priority**: Losing records or corrupting migration history is irreversible and undermines every downstream feature.

**Independent Test**: Soft-delete a record, confirm it is absent from the default manager and present in the deleted-records manager, restore or hard-delete it, confirm an audit entry exists, then change a model and confirm a new migration is generated without modifying existing migration files.

**Acceptance Scenarios**:

1. **Given** any domain model, **When** a record is deleted, **Then** the default manager excludes it, a deleted-records manager includes it, and a physical-delete operation is available for explicit administrative use.
2. **Given** any domain model, **When** a record is created, updated, or deleted, **Then** an audit entry records the change and the acting user when one is available.
3. **Given** a model change, **When** migrations are generated, **Then** a new migration file captures the change and no existing migration file is edited.
4. **Given** database access in application code, **When** a developer reads or writes data, **Then** they use the Django ORM directly rather than a repository abstraction.
5. **Given** a soft-delete requirement, **When** a developer implements it, **Then** the shared manager and base model in the shared utilities application provide the behavior, and no third-party soft-delete library or per-model flag check is introduced.

---

### User Story 4 - Operable, secure, and testable delivery (Priority: P2)

An operator runs background work through the configured task backend, reads structured JSON logs, and relies on documented security controls. A developer writes tests for every behavior change using the mandated framework and confirms the production image builds from the documented Dockerfile.

**Why this priority**: These controls keep the service debuggable, secure, and reproducible in production. They are lower priority than the structural and data guarantees because they can be verified after the core contract is in place.

**Independent Test**: Enqueue a background task through the configured backend, inspect a log line and confirm it is JSON at the expected level, verify secrets are absent from the repository, run the test suite for a changed behavior, and build the production image.

**Acceptance Scenarios**:

1. **Given** background work, **When** a task is dispatched, **Then** it is defined with the framework task decorator in the owning application and enqueued through the configured backend rather than called directly.
2. **Given** a deployment, **When** the task backend is selected, **Then** the selection comes from settings and the application code does not assume a specific backend.
3. **Given** a running service, **When** it emits a log entry, **Then** the entry is structured JSON at one of the documented levels and hot paths avoid per-item log flooding.
4. **Given** a behavior change, **When** a developer delivers it, **Then** a regression test covers the changed behavior and the test suite passes.
5. **Given** a production deployment, **When** the image is built, **Then** it is built from the production Dockerfile at the project root and the service runs behind a WSGI interface.
6. **Given** the repository, **When** a reviewer inspects it, **Then** secrets are provided through environment variables, a committed environment template documents required variables, and no credential is committed.

---

### User Story 5 - Class-based business logic and backward-compatible services (Priority: P2)

A developer adds business behavior and finds it in a class-based service with a versioned contract. When a contract must change incompatibly, a new service version is added alongside the old one so existing callers keep working.

**Why this priority**: This keeps business logic reviewable and prevents silent breakage of callers during refactors.

**Independent Test**: Locate a business rule and confirm it lives in a class-based service, then introduce an incompatible service change and confirm the old version remains available while a new version is added.

**Acceptance Scenarios**:

1. **Given** a business rule, **When** a developer implements it, **Then** it lives in a class-based service rather than a loose function or a view.
2. **Given** an existing service contract, **When** a change cannot remain backward compatible, **Then** a new versioned service is added and the old version remains untouched.
3. **Given** a choice between a maintained library and custom code, **When** the library covers the need, **Then** the library is used and any custom implementation is justified in writing.

---

### User Story 6 - Pipeline domain separated from the operator console (Priority: P1)

A developer works on the crawl, capture, extraction, classification, plan, replay, and
alert lifecycle and finds all of that domain code in a dedicated pipeline application.
The operator console keeps only the operator-facing approval and console surface and
reaches the pipeline through its declared interface. No pipeline model, service, task,
or helper remains inside the admin console application.

**Why this priority**: The pipeline is the largest and most change-prone domain. Keeping
it inside the admin console mixes operator presentation with crawling and extraction
logic, which makes both harder to test and review.

**Independent Test**: Inspect the admin console application and confirm it contains no
pipeline model, stage service, task, discovery client, LLM helper, or artifact helper;
then confirm the pipeline application owns those concerns and the operator console
still serves its endpoints through the pipeline interface.

**Acceptance Scenarios**:

1. **Given** the backend application list, **When** a developer inspects it, **Then** a dedicated pipeline application exists and owns the site, link, capture, extraction, classification, plan, replay, alert, and cost-ledger models.
2. **Given** the admin console application, **When** a developer inspects its models and services, **Then** no pipeline domain model or pipeline stage implementation remains there.
3. **Given** an operator console endpoint that triggers pipeline work, **When** it runs, **Then** it calls the pipeline application's declared interface or service rather than importing pipeline internals directly.
4. **Given** a pipeline background task, **When** it is defined, **Then** it lives in the pipeline application's task module and is enqueued through the configured backend.
5. **Given** the notification application, **When** a developer inspects the project, **Then** the application and all references to it are removed.

---

### Edge Cases

- A model is added without inheriting the shared soft-delete base: the contract review must reject it before merge.
- A response is assembled as a hand-built dictionary instead of a serializer: the contract review must reject it.
- A request body is validated with Pydantic at the API boundary: the contract review must reject it.
- A view reimplements routing through a custom `as_view` override: the contract review must reject it.
- A service signature must change incompatibly: the old version must remain and a new version directory must be introduced.
- A task is called directly instead of enqueued: the contract review must reject it.
- A developer edits an existing migration to reflect a model change: the contract review must reject it.
- A runtime-tunable threshold is hard-coded: the contract review must reject it.
- A new API version is introduced for a non-breaking change: the contract review must reject it.
- A pipeline model or stage service is left in the admin console application: the contract review must reject it.
- The admin console imports a pipeline model directly instead of using the pipeline interface: the contract review must reject it.
- A removed notification reference remains in settings, URLs, services, or tests: the contract review must reject it.
- A pipeline model move changes the application label but keeps the existing table name: migration dependencies must be explicit and the table name must not change unless approved.
- A collection is empty or a field is null: the response must serialize `data` as `[]` or `null` consistently and still include the page object for collections.
- A notification reference remains in documentation: the removal is incomplete.
- A pipeline task fails after the operator console has already accepted the enqueue: the link must be parked in `dead_lettered`, an alert must be raised, and the console must show the new state on its next read.
- The task backend is unavailable during an operator request: the endpoint must return `503 task_backend_unavailable`, must not mark the link as queued, and must leave the record in its prior state.
- A soft-deleted record is still referenced by another model: the delete must be refused with a conflict when the relationship requires the record, and optional relationships must be cleared explicitly.
- A caller outside the admin console tries to use the pipeline interface: the call must be refused because the interface is internal and requires an authenticated operator.

## Requirements *(mandatory)*

### Functional Requirements

#### Project Layout and Configuration

- **FR-001**: The backend MUST expose a single management entry point at the backend root, beside the applications package and the project configuration package.
- **FR-002**: The project configuration package MUST separate settings into a base file plus environment-specific development and production files, and MUST provide versioned API route files under the documented version directory.
- **FR-003**: Each application MUST organize models, versioned views, versioned serializers, versioned services, and tests in the documented directories.
- **FR-004**: The models package MUST contain one module per model or cohesive model group, and its initializer MUST only re-export model classes.
- **FR-005**: The service MUST read secrets, database, cache, and queue configuration from environment variables; a committed environment template MUST document the required variables.
- **FR-006**: Logging MUST be structured JSON with a default level of `INFO`.

#### API Contract

- **FR-007**: All API routes MUST live under a versioned base path, and version routing MUST be declared in the versioned route configuration.
- **FR-008**: Endpoints MUST be implemented as DRF viewsets using real generic viewsets, model viewsets, mixins, and actions; a bare viewset is permitted only when no generic viewset or mixin applies.
- **FR-009**: Custom `as_view` overrides that reimplement routing MUST NOT be used.
- **FR-010**: Serializers MUST be versioned under the documented serializer version directories.
- **FR-011**: Every API response body MUST be produced by a serializer; model instances MUST use model serializers and computed or aggregate payloads MUST use serializers.
- **FR-012**: API request bodies MUST be validated by DRF serializers; Pydantic MUST NOT be imported in API or serializer modules.
- **FR-013**: Collection responses MUST use a `data` collection plus an optional `page` object; detail and mutation responses MUST use a `data` object.
- **FR-014**: All API field names MUST be snake_case.
- **FR-015**: Filtering, search, and ordering MUST use the standard filtering library, and pagination MUST use the default page size.
- **FR-016**: CORS, throttling, and CSRF behavior MUST be provided by the standard libraries, with CSRF disabled for token-based API endpoints.
- **FR-017**: A health-check endpoint MUST exist outside the versioned routes.
- **FR-018**: API documentation MUST be generated from the running endpoints and MUST be reachable through the documented documentation route.

#### Authentication and Authorization

- **FR-019**: Authentication MUST be owned by the pre-built accounts application, which owns the custom user model, OTP logic, and token issuance.
- **FR-020**: The only login identifier MUST be the phone number; email and username login MUST NOT be supported.
- **FR-021**: OTP MUST remain the default authentication flow unless a deviation is explicitly approved.
- **FR-022**: Authorization MUST use project default permission classes, with custom permission classes located in the relevant application's permission or versioned view scope.

#### Data Layer

- **FR-023**: Application code MUST use the Django ORM directly and MUST NOT introduce a repository abstraction over it.
- **FR-024**: Every domain model MUST inherit a shared base model that provides soft delete.
- **FR-025**: Soft delete MUST be implemented by a shared manager class in the shared utilities application, exposing default reads that exclude deleted records, a deleted-records read, a soft-delete operation, and an explicit physical-delete operation.
- **FR-026**: Third-party soft-delete libraries and per-model inline deletion flags MUST NOT be used.
- **FR-027**: Audit logging MUST be enabled for every domain model through the standard audit library, with middleware capturing the acting user.
- **FR-028**: Every database change MUST be captured in a new migration; existing migration files MUST NOT be edited.
- **FR-029**: Database table names MUST follow the framework default unless a specific exception is approved.

#### Services and Business Logic

- **FR-030**: Business logic MUST live in class-based services, not in loose functions or views.
- **FR-031**: Library-first, SOLID, and DRY MUST guide implementation choices in that order.
- **FR-032**: Service contracts MUST remain backward compatible; an incompatible change MUST add a new versioned service while leaving the old version untouched.
- **FR-033**: Runtime-tunable values MUST be stored in configuration or models rather than hard-coded in business logic.

#### Background Tasks

- **FR-034**: Background work MUST use the framework task decorator in the owning application's task module.
- **FR-035**: The task backend MUST be selected through settings and MUST NOT be assumed by application code.
- **FR-036**: Tasks MUST be enqueued through the configured backend rather than called directly.

#### Testing

- **FR-037**: Backend tests MUST use the project's mandated test framework, with Faker for test data.
- **FR-038**: Every behavior change MUST ship with a regression test, and tests MUST live under the owning application's tests directory, with version-specific tests in the versioned test directory.
- **FR-039**: The project MUST target at least 80% coverage, while coverage measurement and enforcement remain the DevOps team's responsibility.

#### Security

- **FR-040**: Passwords and OTPs MUST be hashed; phone numbers MAY be stored as-is.
- **FR-041**: OTP abuse protection MUST be provided by the pre-built accounts application.
- **FR-042**: Payment operations and payment webhooks MUST use the organization's dedicated payment library, while wallet and domain-specific payment logic remain in the project's services layer.
- **FR-043**: Secrets MUST never be committed; the environment file MUST be excluded from version control and a template MUST document required variables.

#### Infrastructure

- **FR-044**: The deployment interface MUST be WSGI; ASGI MUST NOT be used.
- **FR-045**: A production Dockerfile MUST exist at the project root, and development MUST run through the framework's development server.
- **FR-046**: Redis MUST be used as the cache backend and as the task broker when a Redis-backed task backend is selected.
- **FR-047**: CI pipelines, pre-commit hooks, and coverage enforcement MUST remain outside this contract.

#### Module Boundaries

- **FR-048**: A dedicated pipeline application MUST own the site, link, capture, trace, table extraction, table classification, plan, replay, alert, and LLM cost-ledger domain models.
- **FR-049**: The pipeline application MUST own the pipeline stage services, background tasks, discovery client, domtrack client, artifact storage helper, event emitters, LLM helper, plan schema, replay engine, table classifier, and pipeline constants.
- **FR-050**: The admin console application MUST retain only the operator-facing approval and console surface, and MUST reach pipeline behavior through the pipeline application's declared interface or services.
- **FR-051**: No pipeline model, stage service, task, or helper module MAY remain inside the admin console application.
- **FR-052**: The notifications application and every reference to it MUST be removed from settings, URL routing, services, tests, and documentation.
- **FR-053**: Error responses MUST use the shared error shape `{"error": {"code", "message", "fields"}}` and MUST be produced by a serializer.
- **FR-054**: Bulk create, update, and delete operations MUST produce an audit entry for each affected record.
- **FR-055**: The frontend client MUST be updated in the same change whenever the response envelope or endpoint path changes.
- **FR-056**: The health check MUST return `{"data": {"status": "ok"}}` and MUST be produced by a serializer.
- **FR-057**: An old API version MUST remain available for at least one release cycle after a new version is introduced and MUST be marked deprecated in the generated documentation.
- **FR-058**: The default page size MUST be 20 unless an environment setting overrides it.
- **FR-059**: Pipeline-specific constants MUST live in `apps/pipeline/constants.py`; shared and environment-specific values MUST live in settings or django-constance.
- **FR-060**: The operator console surface MUST be limited to the approval queue, verification decisions, and the documented operator endpoints.
- **FR-061**: Operator endpoints that only enqueue pipeline work MUST return an accepted response within 2 seconds at the 95th percentile.
- **FR-062**: Pipeline events that cross into the operator console MUST use structured JSON logs with the event name and identifiers.
- **FR-063**: When the task backend is unavailable during an operator request, the endpoint MUST return `503` with error code `task_backend_unavailable`, MUST NOT mark the record as queued, and MUST leave the record in its prior state.
- **FR-064**: When a pipeline task fails after the console accepted the enqueue, the link MUST be parked in `dead_lettered`, an alert MUST be raised, and the console MUST reflect the new state on its next read.
- **FR-065**: A soft delete MUST be refused with a conflict when another model still references the record through a required relationship; optional relationships MUST be cleared explicitly before the soft delete.
- **FR-066**: The pipeline interface MUST be internal to the backend, MUST require an authenticated operator actor, MUST enforce the same permission checks as the operator console, and MUST NOT be exposed as an HTTP endpoint.

### Key Entities

- **Application module**: A backend application with its own models, versioned views, serializers, services, tasks, and tests.
- **Versioned API route**: A route group mounted under a version segment and declared in the versioned route configuration.
- **Serializer contract**: The versioned request/response shape that defines validation and output for an endpoint.
- **Soft-delete base and manager**: The shared model and manager pair that hide deleted records by default and expose recovery and physical deletion.
- **Audit entry**: The recorded history of a model change and its acting user.
- **Migration**: An immutable, ordered database schema change.
- **Service version**: A class-based business contract that can be superseded without breaking existing callers.
- **Task**: A unit of background work defined with the framework decorator and enqueued through the configured backend.
- **Pipeline application**: The backend application that owns crawling, capture, extraction, classification, plan, replay, alert, and LLM cost-ledger behavior.
- **Admin console application**: The backend application that owns the operator approval queue and operator console endpoints, and delegates pipeline behavior to the pipeline application.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new developer can locate the entry point, settings, routes, and every application's model/view/serializer/service/test location in under 5 minutes using only the repository documentation.
- **SC-002**: 100% of API endpoints return serializer-produced bodies with the documented envelope and snake_case fields.
- **SC-003**: 100% of API request bodies are validated by DRF serializers, and no API or serializer module imports Pydantic.
- **SC-004**: 100% of domain models inherit the shared soft-delete base and are registered for audit logging.
- **SC-005**: Every model change produces a new migration, and no existing migration file is modified.
- **SC-006**: 100% of background tasks are defined with the framework decorator and dispatched through the configured backend.
- **SC-007**: The full backend test suite passes, and every behavior change in a release includes a regression test.
- **SC-008**: The production image builds from the root Dockerfile, and the service starts behind WSGI.
- **SC-009**: The generated API documentation lists every versioned endpoint and its request/response shape.
- **SC-010**: A contract review finds zero violations of the enforcement gates listed in the backend contract.
- **SC-011**: 100% of pipeline models, stage services, tasks, and helpers live in the pipeline application, and 0 pipeline domain modules remain in the admin console application.
- **SC-012**: 0 references to the notifications application remain in the project.
- **SC-013**: Every error response uses the shared error shape and is serializer-produced.
- **SC-014**: Every bulk mutation produces one audit entry per affected record.
- **SC-015**: The frontend client uses the `data`/`page` envelope and passes its test suite after the change.
- **SC-016**: An unavailable task backend produces a `503 task_backend_unavailable` response and leaves the record unchanged.
- **SC-017**: A soft delete of a referenced record is refused with a conflict, and optional references are cleared before deletion.

## Assumptions

- The backend contract in `backend-rules.md` is the authoritative source for this specification; where the contract and an older project document disagree, the contract wins.
- The project is unpublished, so this specification may require breaking changes to existing code and data without backward-compatibility work.
- The existing accounts application already provides phone-only OTP authentication, token issuance, and OTP abuse protection; this specification does not redesign those flows.
- The standard libraries named by the contract (DRF, django-filter, drf-spectacular, django-auditlog, django-environ, django-constance, django-tasks) remain the selected implementations.
- Runtime-tunable values are stored in django-constance or a model with its own domain identity, while environment-specific values live in settings.
- Cross-module access continues to use declared interfaces, consistent with the project constitution.
- The 80% coverage target is a quality goal; measurement and enforcement are owned by the DevOps team.
- The default page size is 20; this is a reasonable default and can be overridden by an environment setting.
- The test-framework migration covers `backend/src/apps/*/tests/` and any `backend/src/apps/*/tests.py`; the frontend keeps its Vitest suite.
- Pipeline constants are domain constants; environment and deployment values remain in settings.
- The operator console may call pipeline services directly only through the `PipelineInterface`; direct model imports are forbidden.
