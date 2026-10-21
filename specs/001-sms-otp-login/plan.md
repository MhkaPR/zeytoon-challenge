# Implementation Plan: SMS OTP Login (User Frontend & Backend)

**Branch**: `001-sms-otp-login` | **Date**: 2026-10-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-sms-otp-login/spec.md`

## Summary

Deliver phone-number + SMS OTP login for the user-facing frontend and the backend that
serves it. A visitor requests a one-time code, receives it by SMS, submits it, and on
success receives a JWT session; the phone number is the unique identifier and new numbers
create an account implicitly (no separate registration). Sessions return the user to a
validated return URL (or a default page). The feature also exposes a reliable guest
vs. authenticated signal and the three roles (guest, regular user, admin) in the data
model. The admin panel is a separate, restricted-domain application and is explicitly out
of scope. Every tunable value is configurable via Django settings or Django models, and
implementation favors established libraries (SimpleJWT, django-cors-headers, DRF
throttling, django-redis, phonenumbers) over hand-written equivalents.

## Technical Context

**Language/Version**: Python 3.14 (backend), TypeScript 5 / Node 20+ (frontend)

**Primary Dependencies**: Django 6.1.2, Django REST Framework 3.18, djangorestframework-simplejwt (JWT), django-cors-headers (CORS allowlist), django-redis / redis-py (OTP TTL + cache + queues), DRF throttling (rate limits), pydantic (boundary validation), phonenumbers (phone validation), drf-spectacular (OpenAPI contract), pytest + pytest-django (tests). Frontend: Next.js 16.4.2, React 19.3, Tailwind 4.

**Storage**: PostgreSQL (source of truth for users, roles, blocks, lockout state); Redis (OTP codes with TTL, throttle counters, JWT denylist cache). Meilisearch is not involved in this feature.

**Testing**: pytest + pytest-django with DRF `APITestCase`/`APIClient`; fakes for the SMS gateway and time freezing for TTL/expiry. Frontend: Next.js test tooling (Vitest + Testing Library) for the login form states.

**Target Platform**: Linux server (Docker), served in Iran; user frontend is a Next.js web app.

**Project Type**: Web application (backend API + user frontend).

**Performance Goals**: Sustain 100 req/s at peak for the auth endpoints (read-heavy overall profile); OTP verify p95 < 300 ms excluding SMS delivery.

**Constraints**: OTP TTL and all thresholds configurable (settings/models); no full phone number, OTP code, or token in logs; JWT access 15 min / refresh 7 days with rotation + revocation; exact CORS allowlist; CSRF double-submit on state-changing requests; all secrets from environment variables; data and services hosted in Iran.

**Scale/Scope**: Hundreds of providers and many end users; login is a low-volume, security-sensitive path. 2 user stories (P1 login, P2 guest state); ~5 backend endpoints; 1 user-frontend login flow.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|-----------|------|--------|
| I. Product Domain | Login supports the comparison product (identifies users); no unrelated features. | PASS |
| II. Cost and External Resources | No LLM calls in this feature; no ceiling interaction. | PASS (N/A) |
| III. Security and Secrets | Secrets via env only; strong hashing for stored codes; Pydantic boundary validation; token rotation/revocation. | PASS |
| IV. Data Governance | Postgres + Redis hosted in Iran; no external data egress; SMS gateway configured in-country. | PASS |
| V. Architecture | Modular monolith; new `accounts` module accessed via interfaces; Postgres source of truth; Redis for cache/TTL; Docker packaging. | PASS |
| VI. Performance and Scalability | 100 req/s target; throttling protects the hot path. | PASS |
| VII. Observability | Metrics for login outcomes, structured JSON logs, sampled logging, phone masking. | PASS |
| VIII. Quality and Testing | Automated tests for every domain behavior; regression tests for bugs; no trivial tests. | PASS |
| IX. Data Retention | Login/lockout records retained per policy; no price history involved. | PASS |
| X. Crawling Ethics | Not applicable (no crawling in this feature). | PASS (N/A) |
| XI. Authentication | JWT with expiry, refresh, and revocation. | PASS |
| XII. Prefer Established Libraries | SimpleJWT, django-cors-headers, django-redis, DRF throttling, phonenumbers, drf-spectacular used instead of custom code; `python manage.py startapp` for the module. | PASS |
| XIII. Configurable Values | All thresholds/TTLs/allowlists in settings or models; no hard-coded magic numbers. | PASS |

**Post-Phase 1 re-check**: No new violations introduced by the design. Complexity Tracking
is empty (no justified deviations).

## Project Structure

### Documentation (this feature)

```text
specs/001-sms-otp-login/
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
    │   ├── settings.py            # auth/cors/throttle/JWT/OTP settings (env-driven)
    │   └── urls.py                # mounts accounts API + admin
    ├── accounts/                  # NEW module (python manage.py startapp accounts)
    │   ├── models.py              # User, OneTimeCode, LoginAttempt, AuthSettings, BlockedContact
    │   ├── interfaces.py          # public interface other modules may import
    │   ├── services.py            # OTP issue/verify, lockout, session issuing
    │   ├── selectors.py           # read helpers (guest/role resolution)
    │   ├── serializers.py         # DRF input/output + pydantic boundary schemas
    │   ├── api.py                 # DRF views (otp request/verify, refresh, logout, session)
    │   ├── urls.py                # /api/v1/auth/*
    │   ├── throttles.py           # per-phone / per-source throttle classes
    │   ├── sms.py                 # SMS gateway adapter interface + env-configured client
    │   ├── admin.py               # operator management of users, blocks, contact channels
    │   └── tests/
    │       ├── test_otp_request.py
    │       ├── test_otp_verify.py
    │       ├── test_lockout.py
    │       ├── test_jwt_session.py
    │       └── test_log_masking.py
    └── core/                      # unchanged; may expose shared guest middleware later

frontend/
├── app/
│   ├── (auth)/login/page.tsx      # phone entry + OTP entry, countdown, error states
│   └── layout.tsx
├── src/
│   ├── features/auth/             # login UI, hooks, state machine
│   │   ├── LoginForm.tsx
│   │   ├── OtpForm.tsx
│   │   ├── useCountdown.ts
│   │   └── returnUrl.ts           # client-side return-URL handling
│   ├── lib/api/auth.ts            # typed client for /api/v1/auth/*
│   └── lib/session/               # token handling (access in memory, refresh cookie)
└── tests/                         # component tests for login states
```

**Structure Decision**: Web application. The backend gains one new module, `backend/src/accounts`,
created with `python manage.py startapp accounts` and registered in `INSTALLED_APPS`. Other
modules reach it only through `accounts/interfaces.py` (Principle V). The user frontend gains
a single `/login` route and an `src/features/auth` slice; no admin frontend code is added,
because the admin panel is a separate restricted-domain application (spec FR-012/FR-013).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations. Table intentionally empty.
