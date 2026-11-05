# Torob Challenge — Host & Server Plan Comparison

A Persian-first (RTL) host/server plan **search and comparison** platform. Users browse and
compare hosting plans across providers; providers register a company, get verified, and
manage their listings and credit from a dedicated panel.

This repository is a **modular monolith**: a Django 6 + DRF backend and a Next.js 16
frontend, with PostgreSQL as the source of truth, Redis for cache/throttles, and Meilisearch
for the local search index. All services and data are hosted in Iran.

---

## Features

### 1. SMS OTP Login (`specs/001-sms-otp-login`)

- Phone number is the unique identifier; login is by **SMS one-time code**.
- New phone numbers create an account implicitly on first successful verification — there is
  no separate registration step.
- Sessions are **JWT** (short-lived access token, rotating refresh token in an `httpOnly`
  cookie, server-side denylist revocation).
- A reliable **guest vs. authenticated** signal (`GET /api/v1/auth/session`).
- Return-URL handling: users land back on the page they came from, with an allowlist and a
  default fallback.
- Security: hashed OTPs with TTL in Redis, per-phone and per-source rate limits, failed-attempt
  limits, temporary lockout, exact CORS allowlist, CSRF double-submit, and one-time-code/token
  redaction in logs.

### 2. Company Registration & Company Panel (`specs/002-company-registration-panel`)

- A user can own **multiple companies**; ownership is single-owner and admin-controlled.
- Multi-step registration with **locked steps**: a step opens only after the previous one is
  approved. Step one collects company info (domain, phone, optional internal number, company
  name, representative name); the next step is operator verification.
- Verification is decided by an operator (admin panel is a separate application) and recorded
  in an **append-only history** (outcome, actor, time, note). A not-approved outcome reopens
  step one for correction.
- Mid-step abandonment clears only that step's draft; the user resumes at the same step.
- The panel opens the **full panel** for verified companies and a **"Continue registration"**
  view for pending/rejected ones — including a redirect when the full-panel URL is reached
  directly.
- Plan eligibility gate: a listing can only be created/activated when the company is **both
  verified and charged**, and the block names every missing prerequisite.
- Per-company **credit ledger** (append-only charge/decharge entries); the current credit is
  the running projection of the ledger. Crawl enabling requires a charged account and costs
  no credit.
- Companies are **archived, never hard-deleted**; ownership transfer is admin-only.

### 3. Public browsing (in progress)

Home page, search, service-type chips, filters, and a company directory shell. Search
ranking/results and the crawl engine are owned by separate features.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.14, Django 6.1, Django REST Framework 3.18 |
| Auth | djangorestframework-simplejwt, django-guardian (roles + object permissions) |
| Runtime config | django-constance (database-backed constants) |
| Validation | Pydantic at external boundaries |
| API docs | drf-spectacular (OpenAPI) + Swagger UI |
| Datastores | PostgreSQL (source of truth), Redis (cache, TTL, throttles), Meilisearch (index) |
| Frontend | Next.js 16.4, React 19.3, TypeScript 5, Tailwind CSS 4 |
| UI kit | HeroUI v3 (`@heroui/react`, `@heroui/styles`) + React Aria |
| Testing | pytest + pytest-django (backend), Vitest + Testing Library (frontend) |
| Packaging | Docker + docker-compose |

The design system is documented in `DESIGN.md` (Vercel-inspired, olive accent `#60782e`,
fully RTL Persian). Product scope and governance live in `.specify/memory/constitution.md`.

---

## Repository Layout

```
backend/
  src/
    config/        Django project (settings, urls, wsgi/asgi)
    accounts/      OTP login, users, roles, JWT, throttling, SMS gateway
    companies/     Registration steps, verification history, panel, credit ledger, crawl
    utils/         Shared TimestampedModel base + structured JSON logging
    catalog/       (scaffolded) plan catalog
    crawler/       (scaffolded) crawl engine
    search/        (scaffolded) search + index
    normalizer/    (scaffolded) provider data normalization
    reranker/      (scaffolded) result reranking
    analytics/     (scaffolded) metrics
    panel/         (scaffolded; panel logic lives in `companies`)
frontend/
  app/             Next.js App Router pages (home, search, companies, panel, login, about)
  src/features/    auth, company, panel, home, search, site feature modules
  src/lib/         Typed API clients (auth, companies), i18n strings, session
  tests/           Vitest + Testing Library tests
specs/             Feature specifications, plans, data models, contracts, quickstarts
.specify/          Spec Kit scaffolding + project constitution
DESIGN.md          Design system (colors, typography, components)
docker-compose.yaml Local orchestration (db, redis, meilisearch, backend)
```

---

## Getting Started

### Prerequisites

- Python 3.14 and [uv](https://docs.astral.sh/uv/)
- Node 20+ and Yarn 1.22
- Docker (for PostgreSQL / Redis / Meilisearch, or run them locally)

### 1. Backend

```bash
# install dependencies into the project virtualenv
uv sync

# start the datastores
docker compose up -d db redis meilisearch

# migrate and create an operator (admin) account
cd backend/src
python manage.py migrate
python manage.py createsuperuser   # prompts for --phone_number
python manage.py runserver 0.0.0.0:8000
```

Local development defaults to SQLite; set `DB_ENGINE=postgresql` (with the `POSTGRES_*`
variables) to use PostgreSQL, which is the production source of truth.

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

Open [http://localhost:3000](http://localhost:3000). By default the app calls the API on its
own origin (`/api/v1/...`) and Next proxies those requests to the backend, so the httpOnly
refresh cookie is first-party and the session survives a page reload. Set
`NEXT_PUBLIC_API_BASE_URL` to an absolute backend origin only for a split-host deployment
(then the proxy is disabled and the browser calls that origin directly).

Frontend runtime values (catalog price step/page sizes, resource options, contact and social
links, ops polling intervals, and the default capture duration) are stored in
django-constance. Edit them from the operator settings page at `/ops/settings`; the SPA
loads the resolved values from `GET /api/v1/catalog/site-config`.

### 3. Full stack with Docker

```bash
docker compose up --build
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
| GET | `/{id}/credit` | Current credit (ledger projection) |
| POST | `/{id}/credit/movements` | Append a charge/decharge entry |
| POST | `/{id}/crawl` | Enable crawl (requires charged account) |
| POST | `/{id}/transfer-ownership` | Always refused; admin-coordinated |

Full request/response contracts live in `specs/*/contracts/`.

---

## Configuration

All secrets and environment-specific values come from environment variables; runtime-tunable
values live in **django-constance** database constants (editable in the admin) so operators
can change thresholds without a redeploy.

### Environment variables (backend)

| Variable | Purpose | Default |
|----------|---------|---------|
| `DJANGO_SECRET_KEY` | Django secret key | dev-only value |
| `DJANGO_DEBUG` | Debug mode | `True` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed hosts | `localhost,127.0.0.1` |
| `DB_ENGINE` | `sqlite` or `postgresql` | `sqlite` |
| `SQLITE_TIMEOUT` | Seconds SQLite waits for a write lock before failing | `20` |
| `POSTGRES_DB/USER/PASSWORD/HOST/PORT` | PostgreSQL connection | `torob` / `localhost:5432` |
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
`COMPANY_REQUIREMENT_MESSAGES`, `COMPANY_STEP_LOCKED_MESSAGE`, `COMPANY_EMPTY_STATE_MESSAGE`.

### Frontend

| Variable | Purpose | Default |
|----------|---------|---------|
| `NEXT_PUBLIC_API_BASE_URL` | Absolute backend base URL; when unset the frontend uses a same-origin `/api/*` proxy (see below) | unset (proxy to `http://localhost:8000`) |
| `API_INTERNAL_BASE_URL` | Backend origin used by server components when `NEXT_PUBLIC_API_BASE_URL` is unset; set this in Docker/container deployments where the backend hostname differs from `localhost` | `http://localhost:8000` |

---

## Testing

```bash
# backend (from repo root)
.venv/bin/python -m pytest backend/src -q

# a single module
.venv/bin/python -m pytest backend/src/companies/tests -q

# frontend
cd frontend && yarn test
```

Backend tests use pytest-django with DRF's API client, a fake SMS gateway, and time freezing
for TTL/expiry. Coverage includes OTP contracts, implicit signup, lockout, throttling, return
URLs, role resolution, log redaction, registration, step locking, mid-step abandonment,
verification-history immutability, panel routing/scoping, plan eligibility, the credit ledger,
crawl gating, and archival. Each feature ships a `quickstart.md` with an end-to-end validation
script.

---

## Project Governance

The project constitution (`.specify/memory/constitution.md`) defines binding principles:
modular monolith with interface-only boundaries, PostgreSQL as source of truth, secrets via
environment variables only, Pydantic validation at every boundary, structured JSON logging,
mandatory automated tests, configurable (never hard-coded) tunables, and a preference for
established libraries and framework generators over hand-written equivalents.

Features are developed spec-first: each lives under `specs/NNN-name/` with `spec.md`,
`plan.md`, `data-model.md`, `contracts/`, and `quickstart.md`.

---

## License

MIT — see `LICENSE`.
