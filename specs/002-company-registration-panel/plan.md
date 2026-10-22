# Implementation Plan: Company Registration & Company Panel

**Branch**: `002-company-registration-panel` | **Date**: 2026-10-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-company-registration-panel/spec.md`

## Summary

Deliver company registration and the company panel for the host/server aggregator. An
authenticated user submits a standalone company-information form (domain, company phone
number, optional internal number, company name, representative name); submitting creates a
company under their single ownership in a pending-verification state flagged unverified.
Registration is modeled as discrete, independently saved steps that stay locked until the
preceding step is approved: step one is company information and the next step is operator
verification. Verification is decided outside this feature's UI and recorded in an
append-only, immutable history (outcome, actor, time, note); a not-approved outcome reopens
step one for correction while the rejection stays in history. The company panel lets a user
own and switch between multiple companies, shows an empty state with "Register new company"
when none exist, opens the full panel for verified companies, and shows a
"Continue company registration" view (with step completion and routing to the current step)
for pending or rejected companies — including a redirect when the full-panel URL is reached
directly. Company-scoped commercial rules expose an eligibility gate that blocks plan actions
unless the company is both verified and charged (naming every missing prerequisite), model
per-company charge status and credit as an append-only credit ledger whose projection is the
company's current credit, and allow crawl enabling only for charged accounts at no credit
cost. Ownership stays admin-only, and companies are archived (never hard-deleted). What a
company publishes is a **plan** (host/server offering), whose entity and management UI are
owned by another feature and are out of scope here, as are duplicate-company detection (the
admin panel's job) and payment/charging. Every tunable value is a django-constance runtime
constant, and the design prefers established libraries and framework generators.

## Technical Context

**Language/Version**: Python 3.14 (backend), TypeScript 5 / Node 20+ (frontend)

**Primary Dependencies**: Django 6.1.2, Django REST Framework 3.18, django-guardian (role +
object-level permissions), django-constance with the database backend (runtime constants),
Pydantic (boundary validation), drf-spectacular (OpenAPI contract), pytest + pytest-django
(tests). Reuses the existing `accounts` JWT auth and `utils` shared base/logging. Frontend:
Next.js 16.4.2, React 19.3, Tailwind 4, Vitest + Testing Library.

**Storage**: PostgreSQL (source of truth for companies, registration steps, verification
history, charge status, and the credit ledger). Redis backs cache/throttles, may hold
short-lived registration-draft TTLs, and may cache the credit projection (the ledger remains
the source of truth). Meilisearch is not involved (search/ranking out of scope).

**Testing**: pytest + pytest-django with DRF `APITestCase`/`APIClient` covering registration,
step locking, mid-step abandonment, append-only verification history, panel routing and
scoping, plan eligibility gating, credit-ledger projection, crawl gating, archival, and log
masking.
Frontend: Vitest + Testing Library for the registration forms, continue view, panel switcher,
and empty state.

**Target Platform**: Linux server (Docker), served in Iran; user frontend is a Next.js web app.
The admin/operator panel is a separate restricted-domain application and is out of scope.

**Project Type**: Web application (backend API + user frontend), modular monolith.

**Performance Goals**: Sustain 100 req/s at peak for panel/registration endpoints
(read-heavy overall profile); company list and panel-entry resolution p95 < 300 ms.

**Constraints**: Company-scoped authorization on every request (owner-only); verification
history and credit ledger append-only and immutable; no company hard-deletion; all tunables
runtime-configurable; no full phone number in any log (reuse `utils.logging` masking); no LLM
calls; single-owner model with no automatic ownership change; data and services hosted in Iran.

**Scale/Scope**: Hundreds of providers/companies and many end users; a user may own any number
of companies. 5 user stories (P1 registration, P2 panel entry/switching/continue view,
P3 verification decision + log, P4 plan eligibility + credit + crawl, P5 business rules), ~10
backend endpoints in the `companies` module, and the user-frontend registration + panel routes.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|-----------|------|--------|
| I. Product Domain | Company registration/panel and plan-eligibility gating directly serve provider data ingestion and the comparison product. | PASS |
| II. Cost and External Resources | No LLM calls; no ceiling interaction in this feature. | PASS (N/A) |
| III. Security and Secrets | Secrets via env only; Pydantic boundary validation on all inputs; owner-only object access; no phone numbers in logs. | PASS |
| IV. Data Governance | Postgres (source of truth) + Redis hosted in Iran; no external egress. | PASS |
| V. Architecture | Modular monolith; one new `companies` app created with `python manage.py startapp`; other modules access it only through `interfaces.py`; Postgres source of truth; Docker packaging. | PASS |
| VI. Performance and Scalability | 100 req/s target; Redis caching and owner-scoped indexed queries on the hot panel path. | PASS |
| VII. Observability | Structured JSON logs for verification decisions, plan-prerequisite refusals, credit movements, ownership refusals, archival; sampling on hot paths; phone masking. | PASS |
| VIII. Quality and Testing | Every domain behavior (step locking, append-only history, prerequisites, scoping, archival) ships with an automated test. | PASS |
| IX. Data Retention | Companies archived, never hard-deleted; verification history and credit ledger retained, append-only, and retrievable. | PASS |
| X. Crawling Ethics | This feature only models the per-company crawl enable switch and its charged precondition; the crawl engine itself is out of scope. | PASS |
| XI. Authentication | Reuses the existing JWT (SimpleJWT) auth from the `accounts` feature; operator decisions are guarded by the `admin` role/guardian perms. | PASS |
| XII. Prefer Established Libraries | Pydantic validation, django-guardian permissions, django-constance constants, drf-spectacular contracts, `startapp` generators; no hand-written equivalents. | PASS |
| XIII. Configurable Values | Step definitions, prerequisite messages, and similar tunables are django-constance database constants; no hard-coded magic numbers. | PASS |

**Post-Phase 1 re-check**: No new violations introduced by the design. Complexity Tracking is
empty (no justified deviations).

## Project Structure

### Documentation (this feature)

```text
specs/002-company-registration-panel/
├── plan.md              # This file ($speckit-plan command output)
├── research.md          # Phase 0 output ($speckit-plan command)
├── data-model.md        # Phase 1 output ($speckit-plan command)
├── quickstart.md        # Phase 1 output ($speckit-plan command)
├── contracts/           # Phase 1 output ($speckit-plan command)
└── tasks.md             # Phase 2 output ($speckit-tasks command - NOT created by $speckit-plan)
```

### Source Code (repository root)

```text
backend/
└── src/
    ├── config/
    │   ├── settings.py            # register companies; add CONSTANCE_CONFIG keys
    │   └── urls.py                # mount /api/v1/companies/
    ├── utils/                     # unchanged (TimestampedModel, logging/masking reused)
    ├── accounts/                  # unchanged (owner FK target, JWT auth, role checks)
    ├── companies/                 # NEW module (python manage.py startapp companies)
    │   ├── models.py              # Company, CompanyStepProgress, VerificationDecision,
    │   │                          #   CompanyRegistrationDraft, CreditLedgerEntry
    │   ├── interfaces.py          # the only sanctioned entry point for other modules
    │   ├── services.py            # register/step-save/abandon, record decision, archive,
    │   │                          #   charge/flags, credit ledger writes + projection,
    │   │                          #   plan eligibility check, ownership refusal
    │   ├── selectors.py           # owner-scoped reads, step-progress/current-step resolution,
    │   │                          #   credit projection reads
    │   ├── serializers.py         # DRF I/O + Pydantic boundary schemas
    │   ├── api.py                 # DRF views for registration, operator decision, panel
    │   │                          #   entry/switch/continue view, plan gate, credit, crawl
    │   ├── urls.py                # /api/v1/companies/*
    │   ├── constants.py           # constance CONSTANCE_CONFIG additions (runtime tunables)
    │   ├── admin.py               # operator: decide verification, set charge/credit, review signals
    │   └── tests/
    │       ├── test_registration.py
    │       ├── test_step_locking.py
    │       ├── test_mid_step_abandonment.py
    │       ├── test_verification_history.py
    │       ├── test_plan_eligibility.py
    │       ├── test_credit_ledger.py
    │       ├── test_panel_entry.py
    │       ├── test_company_switching.py
    │       ├── test_owner_scoping.py
    │       ├── test_archival_ownership.py
    │       └── test_log_masking.py
    └── (no other module)          # plans are owned by another feature; this feature exposes
                                   #   only the plan-eligibility gate + crawl flag. There is no
                                   #   separate `panel` app: the panel endpoints live in
                                   #   `companies`.

frontend/
├── app/
│   ├── panel/page.tsx             # panel shell: empty state + company switcher
│   └── panel/[companyId]/page.tsx # verified → full panel; else continue view (route guard)
├── src/
│   ├── features/company/          # registration form, step progress, continue view
│   │   ├── CompanyForm.tsx
│   │   ├── StepProgress.tsx
│   │   └── ContinueRegistration.tsx
│   ├── features/panel/            # switcher, empty state, full-panel shell
│   │   ├── CompanySwitcher.tsx
│   │   ├── EmptyState.tsx
│   │   └── useActiveCompany.ts
│   ├── lib/api/companies.ts       # typed client for /api/v1/companies/*
│   └── lib/i18n/strings.ts        # add Persian copy for the new views
└── tests/                         # component tests for forms, continue view, switcher
```

**Structure Decision**: Web application, modular monolith. A single scaffolded-but-empty app
becomes the real module: `companies`, registered in `INSTALLED_APPS`, owns the entire company
domain — registration and steps, verification history, charge status, the append-only credit
ledger and its projection, crawl flag, the plan-eligibility gate, archival, ownership rules,
**and the panel entry/switching endpoints**. There is no separate `panel` app: the panel is a
user-facing surface over the same company domain, so its services and views live in
`companies/services.py` and `companies/api.py` with routes in `companies/urls.py`. Other
modules reach the domain only through `companies/interfaces.py` (Principle V). The plan entity
and its management UI are owned by another feature, so no `catalog`/plan module is created
here; this feature exposes only the eligibility gate that a plan-owning feature calls.
Duplicate-company detection lives in the admin panel, so no duplicate-signal model or constant
exists here. The user frontend gains `/panel` and
`/panel/[companyId]` routes plus `src/features/company` and `src/features/panel` slices; no
admin-frontend code is added, because the admin/operator panel is a separate restricted-domain
application.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations. Table intentionally empty.
