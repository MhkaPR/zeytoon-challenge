# Zeytoon · زیتون

**Zeytoon** (زیتون, "olive") is a Persian-first (RTL) **host and server plan search and
comparison engine**. Visitors compare pricing, resources, and server location across
providers in one place. Providers register a company, get verified, and manage their plans,
credit, and crawl lifecycle from a dedicated panel. Operators run verification and the
automated site-data pipeline from a separate admin console.

The product is built as a **modular monolith**: a Django 6 + DRF backend and a Next.js 16
frontend, with PostgreSQL as the source of truth and Redis for cache and throttling. All
services and data are hosted in Iran.

The visual identity is a clean white canvas, black text, and a restrained **olive accent**
(`#60782e`), fully RTL and Persian-first. See [`DESIGN.md`](DESIGN.md).

Link of Demo: https://zeytoon.mhkapr.ir

![Zeytoon home page](imgs/home.png)
---

## Table of Contents

- [Why Zeytoon](#why-zeytoon)
- [Challenges Solved](#challenges-solved)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Repository Layout](#repository-layout)
- [Getting Started](#getting-started)
- [API Overview](#api-overview)
- [Recommendation Engine](#recommendation-engine)
- [Configuration](#configuration)
- [Testing](#testing)
- [Project Governance](#project-governance)
- [License](#license)

---

## Why Zeytoon

Hosting shoppers face a fragmented market: every provider publishes plans in a different
layout, with different units and different names for the same resource. Zeytoon turns that
into one normalized, comparable catalogue:

- **One search surface** for shared, VPS, dedicated, and related hosting plans.
- **Structured comparison** on price, CPU, RAM, disk, traffic, location, OS, and more.
- **Personalized ordering** that learns from anonymous browsing and carries into the account.
- **Explainable recommendations** that tell the visitor *why* a plan is suggested, in real
  units and human language — never raw normalized scores.
- **A trustworthy supply side**: verified companies and an auditable automated pipeline that
  keeps plan data fresh.

---

## Challenges Solved

These are the hard problems the implementation had to solve, and how the codebase addresses
them. Each one maps to a spec and a test suite.

### 1. Anonymous-first personalization without accounts

Most visitors never sign in, so recommendation state cannot depend on a user row. **Solution:**
an opaque, device-scoped visitor cookie set by Next middleware, a per-visitor interest profile,
and a merge matrix on login/logout. The device profile is folded into the account on sign-in
(account history wins), and cleared on sign-out for privacy. The visitor identity is a random
opaque value — no fingerprinting, no personal data in the profile.

### 2. Deterministic cold start

Personalization must not make the catalogue feel random for first-time visitors. **Solution:** a
stable, deterministic cold-start ordering identical for every viewer with no signals, and a
single neutral prior for every dimension. Tests assert byte-identical output on repeated loads.

### 3. Multiple simultaneous interests instead of one averaged vector

Averaging "cheap" and "premium" clicks produces a meaningless middle. **Solution:** bounded
interest clusters, each with its own position and uncertainty. Nearby signals update an existing
cluster; distant signals create a new one until the cap; the least confident cluster is replaced
when full. Clusters are never averaged together for explanations.

### 4. Recency without unbounded influence

Old interests should fade, but repeated clicks must not dominate forever. **Solution:** a
Kalman-style update with time-based uncertainty growth, a per-signal weight, and a decay rate.
The Kalman module is the only place that mutates a node's position or uncertainty, which keeps
the math auditable and testable.

### 5. Semantic understanding of Persian plan titles

Plan titles are short, mixed-script, and inconsistent. **Solution:** character n-gram hashing
(`char_wb`) followed by PCA, min-max scaled into `[0, 1]` so semantic dimensions share the same
distance and Kalman update as explicit attributes. Empty or missing titles get a neutral value,
not a penalty.

### 6. Cache eviction and restart safety

Redis is fast but not durable. **Solution:** the fitted plan space is persisted in PostgreSQL;
Redis is only a read-through cache. On an empty cache the system serves from the database, and
if the database has no valid space it rebuilds and persists one. Every record carries a space
version; a mismatch is rebuilt rather than served.

### 7. Explanations that don't drift from the ranking

An explanation computed by a separate endpoint can describe a different space version than the
plans it accompanies. **Solution:** explanations are produced inside the same suggested-plans
response, keyed to the active space version, and are not stored separately. Deterministic
wording and ranges are asserted in tests.

### 8. Duplicate intents across clusters

Two clusters can resolve to the same intent. **Solution:** per-cluster detection, then merge by
intent key into one row with a disjoint, de-duplicated plan list and contiguous `cluster_id`s
(no gaps in the response).

### 9. Commercial rules that cannot be bypassed

Plan actions must respect verification and payment state. **Solution:** a single eligibility gate
that names **every** missing prerequisite, and reliable tracking of commercial account state.

### 10. A resilient, budget-aware crawling pipeline

Provider sites are slow, inconsistent, and change structure. **Solution:** crawl4ai link
discovery, deterministic-then-LLM refiltering, server-side domtrack capture, table
classification, and Pydantic-validated extraction. Compare-driven replay re-runs the LLM only
when a plans table changes. Network errors are tolerated, and LLM-gated work pauses when the
operator's token budget is exhausted.

### 11. Persian-first RTL without a fragmented UI

Persian copy, Latin identifiers, and technical values must coexist. **Solution:** Vazirmatn-first
typography, logical Tailwind utilities (`ms-*`, `me-*`, `start-*`, `end-*`), local `dir="ltr"`
for URLs and domains, HeroUI v3 + React Aria for accessible components, and centralized i18n
catalogs.

---

## Architecture

```
                         ┌──────────────────────────────┐
                         │        Next.js 16 (RTL)      │
                         │  App Router · HeroUI · i18n  │
                         └──────────────┬───────────────┘
                                        │ /api/* same-origin proxy
                         ┌──────────────▼───────────────┐
                         │        Django 6 + DRF        │
                         │  modular monolith · /api/v1  │
                         └───┬────────┬────────┬────────┘
                             │        │        │
              ┌──────────────▼─┐ ┌────▼─────┐
              │  PostgreSQL    │ │  Redis   │
              │ source of truth│ │ cache/TTL│
              └────────────────┘ └──────────┘
                             │
              ┌──────────────▼───────────────────────────────┐
              │  apps: accounts · companies · admin_console  │
              │        catalog · recommendations · pipeline  │
              └──────────────────────────────────────────────┘
```

Cross-module access goes through declared interfaces (`apps/*/interfaces.py`); modules do not
reach into each other's tables. `apps.catalog` calls the recommendations interface, which owns
the preference model, ranking, and explanations.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.14, Django 6.1, Django REST Framework 3.18 |
| Auth | djangorestframework-simplejwt, django-guardian (roles + object permissions) |
| Runtime config | django-constance (database-backed constants) |
| Validation | Pydantic at external boundaries |
| API docs | drf-spectacular (OpenAPI) + Swagger UI |
| Background tasks | django-tasks-db (database-backed Django Tasks, no Celery) |
| Datastores | PostgreSQL (source of truth), Redis (cache, TTL, throttles) |
| Crawling / capture | crawl4ai, domtrack, LLM extraction against a Pydantic schema |
| Math / ML | NumPy, SciPy (`fisher_exact`), scikit-learn (PCA, hashing vectorizer) |
| Frontend | Next.js 16.4, React 19.3, TypeScript 5, Tailwind CSS 4 |
| UI kit | HeroUI v3 (`@heroui/react`, `@heroui/styles`) + React Aria |
| Testing | pytest + pytest-django (backend), Vitest + Testing Library (frontend) |

The design system is documented in [`DESIGN.md`](DESIGN.md) (olive accent `#60782e`, fully RTL
Persian). Product scope and governance live in `.specify/memory/constitution.md`.

---

## Repository Layout

```
backend/
  src/
    config/               Django project (settings, urls, wsgi/asgi)
    apps/accounts/        OTP login, users, roles, JWT, throttling, SMS gateway
    apps/companies/       Registration steps, verification history, panel, crawl
    apps/admin_console/   Operator approval queue and automated site-data pipeline
    apps/catalog/         Plan catalogue, filters, public browsing contract
    apps/recommendations/ Plan space, signals, clusters, ranking, intent explanations
    apps/pipeline/        crawl4ai discovery, domtrack capture, LLM extraction, replay
    apps/utils/           Shared TimestampedModel base + structured JSON logging
    apps/core/            Shared core helpers
frontend/
  app/             Next.js App Router pages (home, search, companies, panel, login, about, ops)
  src/features/    auth, company, panel, home, search, site, ops feature modules
  src/lib/         Typed API clients, i18n strings, session utilities
  tests/           Vitest + Testing Library tests
specs/             Feature specifications, plans, data models, contracts, quickstarts
.specify/          Spec Kit scaffolding + project constitution
DESIGN.md          Design system (colors, typography, components)
```

---

## Getting Started

### Prerequisites

- Python 3.14 and [uv](https://docs.astral.sh/uv/)
- Node 20+ and Yarn 1.22
- PostgreSQL and Redis running locally (SQLite is the default database for local development,
  but Redis is required for OTP storage, cache, and throttles)

### 1. Backend

```bash
# install dependencies into the project virtualenv
uv sync

# make sure Redis (and PostgreSQL, if used) is running locally

# migrate and create an operator (admin) account
cd backend/src
python manage.py migrate
python manage.py createsuperuser   # prompts for --phone_number
python manage.py runserver 0.0.0.0:8000
```

Local development defaults to SQLite. Set `DATABASE_URL` to a PostgreSQL URL to use the
production source of truth:

```bash
export DATABASE_URL="postgresql://zeytoon:zeytoon@localhost:5432/zeytoon"
```

In development the SMS gateway defaults to `ConsoleSmsGateway`, so OTP codes appear in the
backend log instead of being sent.

- API base: `http://localhost:8000/api/v1/`
- OpenAPI schema: `http://localhost:8000/api/schema/`
- Swagger UI: `http://localhost:8000/api/docs/`
- Django admin: `http://localhost:8000/admin/`

### 2. Frontend

```bash
cd frontend
yarn install
yarn dev
```

Open [http://localhost:3000](http://localhost:3000). By default the app calls the API on its own
origin (`/api/v1/...`) and Next proxies those requests to the backend, so the `httpOnly` refresh
cookie is first-party and the session survives a page reload. Set
`NEXT_PUBLIC_API_BASE_URL` to an absolute backend origin only for a split-host deployment (then
the proxy is disabled and the browser calls that origin directly).

Frontend runtime values (catalog price step/page sizes, resource options, contact and social
links, ops polling intervals, and the default capture duration) are stored in django-constance.
Operators read and update them through `GET/PUT /api/v1/ops/settings`; the SPA loads the
resolved public values from `GET /api/v1/catalog/site-config`.

### 3. Background workers

Django Tasks (`django-tasks-db`) runs queued work from the database; no Celery is used.

```bash
cd backend/src

# process queued tasks (also recovers interrupted site pipelines on startup)
python manage.py db_worker

# enqueue replays for links that are due
python manage.py run_scheduled_replays

# diagnose and recover the pipeline queue by hand
python manage.py recover_pipelines
```

---

## API Overview

Base path: `/api/v1`. All responses are JSON; errors use a single shape
`{ "error": { "code", "message", "fields" } }`.

### Auth — `/api/v1/auth`

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/otp/request` | Request a one-time code for a phone number |
| POST | `/otp/verify` | Submit the code; returns JWT + refresh cookie |
| POST | `/token/refresh` | Rotate refresh token, issue new access token |
| POST | `/logout` | Revoke tokens and clear the refresh cookie |
| GET | `/session` | Current identity/role, or explicit guest result |

### Companies — `/api/v1/companies`

| Method | Path | Purpose |
|--------|------|---------|
| GET/POST | `/` | List the caller's companies / submit step one |
| GET | `/{id}` | Company detail + step progress |
| POST | `/{id}/steps/{step_key}/abandon` | Clear only the addressed step's draft |
| GET | `/panel-switcher` | Companies for the switcher |
| GET | `/{id}/panel-entry` | Resolve full panel vs. continue-registration |
| GET | `/{id}/panel` | Full panel (verified companies only) |
| POST | `/{id}/verification-decisions` | Operator verification decision (admin only) |
| GET | `/{id}/plan-eligibility` | Prerequisite gate for plan actions |
| POST | `/{id}/credit/movements` | Append a charge/decharge entry |
| POST | `/{id}/crawl` | Enable crawl (requires charged account) |
| POST | `/{id}/links` | Manage the company's crawl links |
| POST | `/{id}/transfer-ownership` | Always refused; admin-coordinated |

### Catalogue & Recommendations — `/api/v1/catalog`

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/plans` | Filtered, sorted, paginated plan catalogue |
| GET | `/plans/suggested` | Suggested plans plus per-cluster intent explanations |
| GET | `/companies` | Public company directory |
| GET | `/companies/recent` | Recently approved companies |
| GET | `/site-config` | Resolved runtime configuration for the SPA |

### Interest Signals — `/api/v1/recommendations`

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/signals` | Record a browsing interest signal (rate-limited) |

### Operator Console — `/api/v1/ops`

The operator API covers approvals, sites, link discovery, captures, table extraction and
classification, plan publishing, replay runs, alerts, runtime settings, the LLM token budget,
and metrics. Key routes:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/approvals` | Pending-company approval queue |
| POST | `/companies/{id}/verification-decisions` | Record an approval decision |
| GET/POST | `/sites` | List or create maintained sites |
| POST | `/sites/{id}/discover-links` | Run crawl4ai link discovery |
| GET/POST | `/sites/{id}/links` | List or manage discovered links |
| POST | `/links/{id}/captures` | Start a server-side domtrack capture |
| POST | `/links/{id}/extractions` | Extract tables from a capture |
| GET/POST | `/links/{id}/plans` | Review or publish extracted plans |
| POST | `/links/{id}/publish` | Publish approved plans to the catalogue |
| GET | `/replay-runs` | Inspect replay runs |
| POST | `/replay-runs/create` | Create a replay run |
| GET/PUT | `/settings` | Read or update runtime constants |
| GET/PUT | `/llm-token-budget` | Read or set the LLM token budget |
| GET | `/metrics` | Pipeline metrics snapshot |

Full request/response contracts live in `specs/*/contracts/`.

---

## Recommendation Engine

The recommendation engine lives in `apps/recommendations` and is exposed to the catalogue only
through `RecommendationsInterface`.

1. **Space fitting** — published plans are normalized into `[0, 1]^d` with existence masks, plus
   ten PCA-derived semantic dimensions from titles.
2. **Signal recording** — destination visit, details view, and search impression are weighted,
   rate-limited per viewer, and stored as events.
3. **Clustering** — Kalman updates maintain bounded interest clusters with position and
   uncertainty; stale clusters decay out of suggestions.
4. **Ranking** — the filtered catalogue is scored in one O(N) pass against each cluster and
   paginated afterwards.
5. **Intent detection** — each cluster's top-K candidates are tested against pre-declared intent
   patterns with statistical-significance, effect-size, and click-corroboration gates.
6. **Explanation** — one human-readable row per distinct intent, merged across clusters, with an
   honest "exploring" fallback.

### Refresh & rebuild commands

```bash
# refresh the semantic plan space (run daily from cron)
cd backend/src && python manage.py refresh_recommendation_space

# rebuild a profile's interest clusters after a state-format change
cd backend/src && python manage.py rebuild_interest_clusters --visitor-id <uuid>

# inspect the fitted space, a viewer's clusters, and the resulting order
cd backend/src && python manage.py analyze_recommendation_space --visitor-id <uuid>

# live simulation for demos and debugging
cd backend/src && python manage.py simulate_recommendations \
  --plan-type dedicated_server --count 5 --top 10 --keep
```

A failed refresh leaves the previous space key intact. The space and explanations are persisted
in PostgreSQL; Redis is only a cache.

---

## Configuration

All secrets and environment-specific values come from environment variables; runtime-tunable
values live in **django-constance** database constants (editable in the admin) so operators can
change thresholds without a redeploy.

### Environment variables (backend)

| Variable | Purpose | Default |
|----------|---------|---------|
| `DJANGO_SECRET_KEY` | Django secret key | dev-only value |
| `DJANGO_DEBUG` | Debug mode | `True` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed hosts | `localhost,127.0.0.1` |
| `DATABASE_URL` | Database connection URL; use PostgreSQL in production | `sqlite:///db.sqlite3` |
| `REDIS_URL` | Redis URL (cache, TTL, throttles) | `redis://localhost:6379/0` |
| `CORS_ALLOWED_ORIGINS` | Exact frontend origin allowlist | `http://localhost:3000` |
| `CSRF_TRUSTED_ORIGINS` | CSRF trusted origins | follows CORS |
| `JWT_ACCESS_MINUTES` / `JWT_REFRESH_DAYS` | Token lifetimes | `15` / `7` |
| `SMS_GATEWAY_BACKEND` | SMS adapter class | `apps.accounts.sms.ConsoleSmsGateway` |
| `SMS_GATEWAY_API_KEY` / `_SENDER` / `_BASE_URL` | SMS gateway credentials | — |
| `OTP_HASH_SECRET` | HMAC key for stored OTP hashes | falls back to `SECRET_KEY` |
| `PHONE_DEFAULT_REGION` | Default region for phone parsing | `IR` |
| `THROTTLE_*` | DRF throttle rates | see `settings.py` |
| `LOG_LEVEL` | Root log level | `INFO` |

### Runtime constants (django-constance)

`OTP_LENGTH`, `OTP_TTL_SECONDS`, `MAX_VERIFY_ATTEMPTS`, `LOCKOUT_THRESHOLD`,
`LOCKOUT_DURATION_SECONDS`, `REQUEST_COOLDOWN_SECONDS`, `REQUEST_HOURLY_CAP`,
`VERIFY_WINDOW_LIMIT`, `VERIFY_WINDOW_SECONDS`, `CONTACT_CHANNELS`,
`RETURN_URL_ALLOWLIST`, `DEFAULT_RETURN_PATH`, `COMPANY_STEP_DEFINITIONS`,
`COMPANY_REQUIREMENT_MESSAGES`, `COMPANY_STEP_LOCKED_MESSAGE`, `COMPANY_EMPTY_STATE_MESSAGE`,
`RECOMMENDATION_SEMANTIC_DIMENSIONS`, `RECOMMENDATION_MAX_INTEREST_CLUSTERS`,
`RECOMMENDATION_CLUSTER_DISTANCE_THRESHOLD`, and the intent-pattern thresholds and
candidate-set size.

### Frontend

| Variable | Purpose | Default |
|----------|---------|---------|
| `NEXT_PUBLIC_API_BASE_URL` | Absolute backend base URL; when unset the frontend uses a same-origin `/api/*` proxy | unset (proxy to `http://localhost:8000`) |
| `API_INTERNAL_BASE_URL` | Backend origin used by server components when `NEXT_PUBLIC_API_BASE_URL` is unset | `http://localhost:8000` |

The Docker Compose frontend sets `API_INTERNAL_BASE_URL` to `http://backend:8000` for server-side
catalog requests and passes the same origin as `API_PROXY_TARGET` at build time for Next.js rewrites.

---

## Testing

```bash
# backend (from repo root)
uv run pytest

# a single module
uv run pytest backend/src/companies/tests -q

# recommendation scenarios
uv run pytest backend/src/apps/recommendations/tests/test_recommendation_scenarios.py -q

# frontend
cd frontend && yarn test
```

Backend tests use pytest-django with DRF's API client, a fake SMS gateway, and time freezing for
TTL/expiry. Coverage includes OTP contracts, implicit signup, lockout, throttling, return URLs,
role resolution, log redaction, registration, step locking, mid-step abandonment,
verification-history immutability, panel routing/scoping, plan eligibility, crawl gating,
archival, recommendation space persistence, clustering, ranking, intent scoring,
merging, determinism, and frontend explanation rendering. Each feature ships a `quickstart.md`
with an end-to-end validation script.

The recommendation system also has a presentation-grade scenario report at
`specs/008-intent-pattern-explanations/recommendation-scenarios-report.md`. It covers cold
start, intent detection, non-click signals, multiple interests, duplicate merging, resource
filtering, decay, profile isolation, rate limiting, the API, and deterministic output.

---

## Project Governance

The project constitution (`.specify/memory/constitution.md`) defines binding principles:
modular monolith with interface-only boundaries, PostgreSQL as source of truth, secrets via
environment variables only, Pydantic validation at every boundary, structured JSON logging,
mandatory automated tests, configurable (never hard-coded) tunables, and a preference for
established libraries and framework generators over hand-written equivalents.

Features are developed spec-first: each lives under `specs/NNN-name/` with `spec.md`, `plan.md`,
`data-model.md`, `contracts/`, and `quickstart.md`.

---

## License

MIT — see [`LICENSE`](LICENSE).
