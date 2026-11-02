# Implementation Plan: Company Wallet and Crawl Eligibility

**Branch**: `004-company-wallet-crawl-gating` | **Date**: 2026-11-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-company-wallet-crawl-gating/spec.md`

## Summary

Implement company wallet funding and an authoritative product ledger, using the installed
`payment==0.0.9` package only to create, verify, and refund provider transactions. Add a
database-backed Constance threshold exposed through Django admin. Use a companies-module
interface for payment credit, eligibility, and reasons; enforce that eligibility at public
catalog reads and before background discovery/capture/replay work. Remove company charge and
crawl switches in favor of derived eligibility, support repeat discovery and company URL
submission, remove the unused per-site crawl query, and display full phone numbers in
authorized UI/API responses while keeping operational logs masked. Item 11 remains
unspecified in the source issue list; its possible requirements are not planned here.

## Technical Context

**Language/Version**: Python 3.14, Django 6.1, Django REST Framework; TypeScript/Next.js frontend.

**Primary Dependencies**: `payment==0.0.9` (PyPI distribution `payment`; module `payment`),
django-constance 4.4 with database backend, Django Tasks (`django.tasks`), django-guardian,
`crawl4ai`, PostgreSQL, Redis.

**Storage**: PostgreSQL source of truth for companies, wallet ledger, provider transaction
references, sites, links, and published plans; Redis for cache/queues and OTP state; trace
artifacts remain in configured object storage.

**Testing**: pytest + pytest-django; Django migration/system checks and focused domain/API,
provider-adapter, worker, catalog visibility, and frontend type/build validation. Automated
tests are required by the constitution, but the plan phase does not execute them.

**Target Platform**: Iran-hosted Linux application services; Django backend and Next.js frontend.

**Project Type**: Web application (modular monolith).

**Performance Goals**: Preserve the constitution's 100 RPS peak-read target and 5-minute
search freshness. Wallet eligibility checks on public catalog reads must not add per-plan
query amplification; worker gates must use batchable company/site eligibility reads.

**Constraints**: Keep module communication behind declared interfaces. The payment package
owns gateway transaction lifecycle, not company balances or wallet ledger. Confirmed provider
transactions must map to exactly one wallet credit. Runtime minimum wallet amount comes from
database-backed Constance. Ineligible companies cannot expose plans or enter discovery,
crawl, capture, or replay. Full phones are permitted in authorized displays but prohibited in
operational logs. Item 11 is unresolved and excluded pending clarification.

**Scale/Scope**: Existing `companies`, `admin_console`, `catalog`, `accounts`, and frontend
company/panel/search/home/ops surfaces, plus a dedicated `pipeline` Django app; company-level
wallet, all eligible public plans, site-level crawl/replay scheduling, and discovered/manual
links.

## Constitution Check

### Pre-Design Gate

- **Product Domain (I)**: Pass. Wallet and ingestion eligibility support provider plan
  listing and comparison.
- **Cost and External Resources (II)**: Pass. No change to LLM ceiling enforcement.
- **Security and Secrets (III)**: Pass with design constraint. Provider API keys remain in
  the payment package's protected `PayPortal`; no secrets in application config responses or
  logs. Validate provider callbacks and payment state before wallet credit.
- **Data Governance (IV)**: Pass with deployment constraint. Persist payment and wallet data
  in the existing Iran-hosted PostgreSQL deployment.
- **Architecture (V)**: Pass with explicit interfaces. Company wallet and eligibility are
  owned by `companies`; provider transaction lifecycle by `payment`; public plan policy and
  records by `catalog`; pipeline models, tasks, integrations, and domain services by the new
  `pipeline` app; operator/admin APIs and presentation by `admin_console`. The console invokes
  pipeline behavior only through `pipeline.interfaces`. No direct cross-module table access.
- **Performance and Scalability (VI)**: Pass subject to bulk eligibility reads and existing
  cache invalidation when company eligibility changes.
- **Observability (VII)**: Pass. Add structured outcome/skip events, aggregate metrics, and
  phone/secret redaction.
- **Quality and Testing (VIII)**: Pass. Add regression tests for each altered behavior.
- **Data Retention (IX)**: Pass. No changes to price history retention.
- **Crawling Ethics (X)**: Pass. Eligibility gate wraps existing compliant crawler behavior.
- **Authentication (XI)**: Pass. Existing JWT and object authorization remain in effect.
- **Established Libraries (XII)**: Pass. Use the already installed payment provider
  integration library and django-constance; do not replace either with custom gateway code.
- **Configurable Values (XIII)**: Pass. Wallet eligibility threshold uses database-backed
  django-constance and is administered in Django admin; no threshold is hard-coded.

No constitution violation requires an exception.

## Project Structure

### Documentation (this feature)

```text
specs/004-company-wallet-crawl-gating/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── payment-wallet.md
│   ├── companies-eligibility.md
│   └── public-catalog.md
└── checklists/requirements.md
```

### Source Code (repository root)

```text
backend/src/
├── config/
│   ├── settings.py                 # payment + pipeline apps and Constance wallet threshold
│   └── urls.py                     # operator routes remain mounted under ops
├── companies/
│   ├── models.py                   # company wallet and append-only wallet entries
│   ├── services.py                 # top-up initiation, idempotent credit, eligibility
│   ├── selectors.py                # wallet and eligibility read models
│   ├── interfaces.py               # sanctioned module boundary
│   ├── api.py                      # wallet and additional URL endpoints
│   ├── urls.py
│   └── admin.py                    # wallet/ledger views if operationally needed
├── admin_console/
│   ├── api.py                      # operator API and authorization
│   ├── serializers.py              # operator request/response validation
│   ├── services.py                 # operator use cases calling pipeline interface
│   └── urls.py                     # operator routes
├── pipeline/                       # new bounded Django app for ingestion lifecycle
│   ├── models.py                   # Site, Link, Trace, extraction/replay state
│   ├── tasks.py                    # discovery, capture, extraction, replay workers
│   ├── services.py                 # pipeline domain workflows
│   ├── interfaces.py               # sanctioned entry point for console/companies
│   ├── events.py                   # pipeline domain events and structured observability
│   ├── constants.py                # pipeline runtime settings accessors
│   ├── llm.py                      # LLM extraction, validation, and budget integration
│   ├── plan_schema.py              # extraction schema definitions
│   ├── table_classifier.py         # pipeline table classification
│   ├── artifacts.py                # trace artifact storage operations
│   ├── admin.py                    # registration/configuration of pipeline records
│   ├── discovery.py                # crawl4ai link discovery adapter
│   ├── domtrack_client.py          # domtrack adapter
│   ├── replay.py                   # replay and comparison workflows
│   ├── management/commands/        # worker recovery and scheduled replay commands
│   ├── migrations/                 # pipeline-owned schema and data moves
│   └── apps.py                     # Django app config
├── catalog/
│   ├── selectors.py                # eligible-only public plan queries
│   ├── services.py                 # publish/withdraw via company interface
│   └── interfaces.py               # public catalog contract
├── accounts/
│   ├── api.py                      # full phone in authorized session responses
│   └── selectors.py                # full phone profile display data
└── utils/migrations/               # generated schema migrations by owning apps

frontend/src/
├── features/panel/                 # wallet balance, payment/top-up, full company phone
├── features/company/               # additional plan URL submission
├── features/ops/                   # discovery refresh and eligibility reason
├── features/auth/                  # full signed-in user phone display
├── features/home/                  # eligible catalog plans
└── features/search/                # eligible catalog plans
```

**Structure Decision**: Keep the modular monolith and separate operator UX from pipeline
domain behavior. `companies` owns the product wallet and eligibility interface; `payment`
owns Iranian provider transactions; `catalog` owns public plan visibility; the new `pipeline`
app owns pipeline data and lifecycle; `admin_console` owns operator/admin routes and calls
`pipeline.interfaces`. Move the current pipeline models, tasks, services, discovery,
domtrack, replay, and related worker commands out of `admin_console` as part of implementation.
More precisely, move `models.py`, `tasks.py`, `discovery.py`, `domtrack_client.py`,
`artifacts.py`, `constants.py`, `events.py`, `llm.py`, `plan_schema.py`, `replay.py`, and
`table_classifier.py` into `pipeline`. Split `services.py`: approval queue and verification
orchestration stay in `admin_console`; ingestion, extraction, classification, labeling,
publishing, replay, and budget operations move to `pipeline.services`. Move pipeline model
registrations and migrations to `pipeline`; keep operator API routes, request serializers,
and app config in `admin_console`, refactoring views to call only `pipeline.interfaces`.
No new deployable service or parallel wallet/payment app is needed.

## Complexity Tracking

No constitution violations are proposed.
