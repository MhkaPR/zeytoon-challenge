# Torob Host & Server Plan Comparison Constitution

<!--
SYNC IMPACT REPORT
==================
Version change: (unratified scaffold) → 1.0.0
Bump rationale: Initial ratification. The file previously contained only the blank
  Spec Kit scaffold with placeholder tokens; this amendment supplies the first set of
  concrete principles, constraints, workflow, and governance rules.

Modified principles:
  - [PRINCIPLE_1_NAME]  → I. Product Domain
  - [PRINCIPLE_2_NAME]  → II. Cost and External Resources
  - [PRINCIPLE_3_NAME]  → III. Security and Secrets
  - [PRINCIPLE_4_NAME]  → IV. Data Governance
  - [PRINCIPLE_5_NAME]  → V. Architecture
  - (new)               → VI. Performance and Scalability
  - (new)               → VII. Observability
  - (new)               → VIII. Quality and Testing
  - (new)               → IX. Data Retention
  - (new)               → X. Crawling Ethics
  - (new)               → XI. Authentication

Added sections:
  - Technology Stack and Constraints (was [SECTION_2_NAME])
  - Development Workflow and Quality Gates (was [SECTION_3_NAME])

Removed sections: none

Deferred items:
  - TODO(MISSING_PRINCIPLE_II): The source input labeled principles "One", then "Three"
    onward, with no "Two". Numbering has been normalized to I–XI; confirm whether a
    missing principle was omitted accidentally and supply it in a follow-up amendment.
  - TODO(GOVERNANCE_APPROVERS): Named approver roles for constitutional amendments are
    not yet defined; see Governance section.
-->

# Torob Host & Server Plan Comparison Constitution

## Core Principles

### I. Product Domain

The product is a host and server plan search and comparison engine.

- Users MUST be able to search and compare plans across hundreds of providers.
- Providers MUST be able to connect their own data into the system.
- Every domain feature MUST serve search, comparison, or provider data ingestion.

Rationale: A single, unambiguous domain keeps scope decisions testable and prevents
drift into unrelated product areas.

### II. Cost and External Resources

- The LLM cost ceiling MUST be configurable through Django models, never hard-coded in
  `settings.py`.
- Exceeding the ceiling MUST trigger automatic LLM shutdown plus an alert to the admin.
- Silent ceiling breaches are FORBIDDEN; every breach MUST be observable and recorded.

Rationale: Unbounded external spend is an existential risk; a model-backed ceiling keeps
the limit runtime-adjustable without redeploys.

### III. Security and Secrets

- Keys and tokens MUST be read only from environment variables; they MUST NOT appear in
  code or in the repository.
- Encryption of sensitive data at rest is mandatory.
- Provider tokens MUST be rotatable and revocable by an admin.
- Poisoned or invalid data MUST be rejected at the point of entry using Pydantic
  validation.

Rationale: Provider credentials are high-value secrets; defense at the boundary keeps
untrusted data out of the source of truth.

### IV. Data Governance

- All data and services (Postgres, Redis, Meilisearch, Docker) MUST be hosted in Iran.
- Meilisearch MUST run locally.

Rationale: Data residency is a legal and operational constraint, not a preference.

### V. Architecture

- The system MUST be a modular monolith: Django 6 + DRF on the backend, Next.js on the
  frontend.
- Communication between modules MUST happen only through interfaces; direct access to
  another module's tables is FORBIDDEN.
- Microservices are FORBIDDEN unless this principle is officially revised.
- PostgreSQL is the source of truth; Meilisearch is only an index.
- Redis is mandatory for caching and queues; Docker is mandatory for packaging.

Rationale: Interface-only boundaries preserve the option to split later while keeping a
single deployable today.

### VI. Performance and Scalability

- The system MUST sustain 100 requests per second at peak load with a read-heavy profile.
- Permissible search staleness: price changes MUST be reflected in search results within
  at most 5 minutes.
- Redis caching for frequent queries is mandatory.

Rationale: Search is the product's hot path; explicit targets make performance
regressions detectable.

### VII. Observability

- Mandatory metrics: crawl success rate per provider, latency per source, number and
  cumulative daily cost of LLM calls, and search staleness.
- Logging MUST be structured JSON at levels `debug`, `info`, `warning`, and `error`
  throughout the code.
- Anti-noise rule: repeated logging inside loops is FORBIDDEN; frequent paths MUST be
  logged with sampling or aggregation to keep log volume under control.

Rationale: Metrics drive operations; sampled structured logs keep signal high without
flooding storage.

### VIII. Quality and Testing

- Every domain behavior MUST have an automated test.
- Forbidden tests: getters/setters, trivialities, basic framework operations, and other
  worthless tests.
- Every fixed bug MUST have a regression test.
- Numeric coverage is NOT the criterion; testing domain behavior is the criterion.

Rationale: Tests exist to protect behavior, not to satisfy a metric.

### IX. Data Retention

- Price history MUST be retained for a 24-month period, then aggregated.

Rationale: Long-horizon price history supports comparison and analytics while bounded
aggregation keeps storage predictable.

### X. Crawling Ethics

- Compliance with `robots.txt` is mandatory.
- A transparent User-Agent accompanied by a contact URL is mandatory.
- Per-domain rate limiting MUST be observed to avoid pressuring providers' servers.

Rationale: Sustainable provider relationships depend on courteous, identifiable crawling.

### XI. Authentication

- User login MUST use JWT.

Rationale: A single, stateless auth mechanism simplifies the API and the Next.js client.

## Technology Stack and Constraints

- Backend: Django 6 + Django REST Framework.
- Frontend: Next.js.
- Data stores: PostgreSQL (source of truth), Redis (cache and queues), Meilisearch
  (local index only).
- Packaging: Docker, with `docker-compose` for local orchestration.
- Hosting: all services and data hosted in Iran.
- Secrets: injected via environment variables only.
- Validation: Pydantic at every external data boundary.
- Cost control: LLM ceiling configurable in Django models, enforced at runtime.

## Development Workflow and Quality Gates

- Module changes MUST cross boundaries only through declared interfaces; reviewers MUST
  reject direct cross-module table access.
- Every domain behavior change MUST ship with an automated test of that behavior; bug
  fixes MUST ship with a regression test.
- Observability MUST be updated alongside features: new metrics, structured logs, and
  sampling where paths are hot.
- Secrets MUST be verified absent from diffs before merge; any leaked credential MUST be
  rotated.
- Performance-sensitive changes MUST state their impact against the 100 RPS and 5-minute
  staleness targets.

## Governance

- This constitution supersedes all other development practices; where a practice
  conflicts with a principle, the principle wins.
- Amendments require a documented proposal, approval by the project maintainers, and a
  migration plan for any behavior already in violation. TODO(GOVERNANCE_APPROVERS):
  name the specific approver roles.
- Versioning policy follows semantic versioning: MAJOR for backward-incompatible
  governance or principle removals/redefinitions, MINOR for new or materially expanded
  principles, PATCH for clarifications and non-semantic refinements.
- Compliance review is required on every PR: reviewers MUST verify the change against
  each affected principle and MUST reject unapproved complexity.
- The Sync Impact Report at the top of this file is temporary review material and MUST be
  removed before the amended constitution is committed.

**Version**: 1.0.0 | **Ratified**: 2026-10-21 | **Last Amended**: 2026-10-21
