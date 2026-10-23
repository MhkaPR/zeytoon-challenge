---

description: "Task list for SMS OTP Login (User Frontend & Backend)"
---

# Tasks: SMS OTP Login (User Frontend & Backend)

**Input**: Design documents from `/specs/001-sms-otp-login/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/auth-api.md

**Tests**: Included. The project constitution (Principle VIII) requires an automated test for
every domain behavior, so test tasks are part of each story.

**Organization**: Tasks are grouped by user story to enable independent implementation and
testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- All paths are relative to the repository root.

## Path Conventions

Web application: backend at `backend/src/`, frontend at `frontend/` (see plan.md).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependency wiring

- [X] T001 Add backend dependencies (`djangorestframework-simplejwt`, `django-guardian`, `django-constance[database]`, `django-cors-headers`, `django-redis`, `phonenumbers`, `drf-spectacular`, `pydantic`, `pytest`, `pytest-django`, `freezegun`) to `pyproject.toml` and install with `uv sync`
- [X] T002 Create the shared `utils` app with `python manage.py startapp utils` and register `utils` in `INSTALLED_APPS` in `backend/src/config/settings.py`
- [X] T003 Create the `accounts` app with `python manage.py startapp accounts` and register `accounts` in `INSTALLED_APPS` in `backend/src/config/settings.py`
- [X] T004 [P] Register `rest_framework`, `rest_framework_simplejwt.token_blacklist`, `guardian`, `corsheaders`, `constance`, and `drf_spectacular` in `INSTALLED_APPS` in `backend/src/config/settings.py`
- [X] T005 [P] Add `corsheaders.middleware.CorsMiddleware` and `django.middleware.csrf.CsrfViewMiddleware` to `MIDDLEWARE` in `backend/src/config/settings.py`
- [X] T006 [P] Configure pytest for Django in `backend/pyproject.toml` or `backend/src/pytest.ini` with `DJANGO_SETTINGS_MODULE=config.settings`
- [X] T007 [P] Configure frontend test tooling (Vitest + Testing Library) in `frontend/package.json` and `frontend/vitest.config.ts`

**Checkpoint**: Both new apps exist, dependencies install, and the test runners are configured.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared infrastructure that MUST exist before any user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T008 Implement the abstract `TimestampedModel` (`created_at = auto_now_add=True, db_index=True`, `updated_at = auto_now=True`, `class Meta: abstract = True`) in `backend/src/utils/models.py`
- [X] T009 [P] Add environment-driven settings to `backend/src/config/settings.py`: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, PostgreSQL `DATABASES` from env, Redis `CACHES` via `django-redis`, `CORS_ALLOWED_ORIGINS` (exact allowlist, no wildcard), `CORS_ALLOW_CREDENTIALS=True`, `SIMPLE_JWT` lifetimes (access 15 min, refresh 7 days, rotate refresh, blacklist after rotation), `CSRF_TRUSTED_ORIGINS`, and `SMS_GATEWAY_*` credential placeholders read from env
- [X] T010 [P] Declare all runtime constants in `CONSTANCE_CONFIG` in `backend/src/config/settings.py` (OTP_LENGTH=6, OTP_TTL_SECONDS=120, MAX_VERIFY_ATTEMPTS=5, LOCKOUT_THRESHOLD=5, LOCKOUT_DURATION_SECONDS=900, REQUEST_COOLDOWN_SECONDS=60, REQUEST_HOURLY_CAP=5, VERIFY_WINDOW_LIMIT=10, VERIFY_WINDOW_SECONDS=600, CONTACT_CHANNELS, RETURN_URL_ALLOWLIST, DEFAULT_RETURN_PATH="/") and set `CONSTANCE_BACKEND = "constance.backends.database.DatabaseBackend"`
- [X] T011 Configure the DRF default throttle classes and rates in `REST_FRAMEWORK` settings in `backend/src/config/settings.py` (anon/user global limits plus scoped throttle names)
- [X] T012 [P] Create the `User` model in `backend/src/accounts/models.py` extending Django's auth user and `TimestampedModel`, with `phone_number` (unique, E.164) and `status` (`active`/`blocked`, default `active`); roles are Django `Group`s (`regular`, `admin`), not a column
- [X] T013 [P] Create the `OTP` and `Attempt` state helpers (Redis-backed, no DB model) in `backend/src/accounts/models.py` or `backend/src/accounts/state.py`: key `otp:{phone}` with `code_hash` (HMAC-SHA256 with a server-side secret), `attempts`, `issued_at`, TTL from `OTP_TTL_SECONDS`; lockout counters keyed by phone and source with TTL
- [X] T014 Define the SMS gateway interface plus an env-configured implementation and a console/fake implementation for tests in `backend/src/accounts/sms.py`
- [X] T015 [P] Add a phone-number validation/normalization helper using `phonenumbers` (E.164, default region from settings) in `backend/src/accounts/validation.py`
- [X] T016 [P] Configure structured JSON logging with the required levels and a masking filter that redacts full phone numbers (keep short prefix/suffix), OTP codes, and tokens in `backend/src/config/settings.py` and `backend/src/utils/logging.py`
- [X] T017 Add `AUTH_USER_MODEL`/user wiring, guardian anonymous-user support (`ANONYMOUS_USER_NAME`), and the constance admin registration in `backend/src/config/settings.py`
- [X] T018 Create the initial migrations for `accounts` and `utils` with `python manage.py makemigrations` and apply them
- [X] T019 Mount the DRF API and drf-spectacular schema routes under `/api/v1/` in `backend/src/config/urls.py`
- [X] T020 [P] Define the shared error response shape (`{"error": {"code", "message", "fields"}}`) and a DRF exception handler in `backend/src/accounts/exceptions.py`
- [X] T021 Create `backend/src/accounts/interfaces.py` exposing the public functions other modules may import (e.g. `get_user_role`, `is_authenticated`, `resolve_current_user`) and document that no other module may touch `accounts` tables

**Checkpoint**: Base model, configuration, constants, logging, masking, and routing are ready.

---

## Phase 3: User Story 1 - Regular user logs in with phone + SMS OTP (Priority: P1) 🎯 MVP

**Goal**: A visitor requests an OTP, receives it by SMS, verifies it, and is logged in with a
JWT session; new phone numbers create the account implicitly and the user returns to a
validated return URL.

**Independent Test**: From a logged-out state, request a code for a new phone number, verify
the correct code, and confirm the user is authenticated and redirected to the originating
page; repeat with the same number and confirm no duplicate account is created.

### Tests for User Story 1 ⚠️

> Write these tests FIRST and ensure they FAIL before implementation.

- [X] T022 [P] [US1] Contract test for `POST /api/v1/auth/otp/request` (200 sent with `expires_in_seconds`; 400 `invalid_phone`; 409 `user_blocked`; 429 `rate_limited`/`locked_out`) in `backend/src/accounts/tests/test_contract_otp_request.py`
- [X] T023 [P] [US1] Contract test for `POST /api/v1/auth/otp/verify` (200 tokens + `redirect_to`; 400 `otp_incorrect`; 409 `user_blocked`; 429 `too_many_attempts`/`locked_out`) in `backend/src/accounts/tests/test_contract_otp_verify.py`
- [X] T024 [P] [US1] Contract test for `POST /api/v1/auth/token/refresh` and `POST /api/v1/auth/logout` in `backend/src/accounts/tests/test_contract_token.py`
- [X] T025 [P] [US1] Domain test: first successful verification creates the user implicitly and a second login with the same phone reuses it (no duplicate) in `backend/src/accounts/tests/test_implicit_signup.py`
- [X] T026 [P] [US1] Domain test: expired or absent code returns exactly "The code is incorrect" and never reveals expiry in `backend/src/accounts/tests/test_otp_expiry.py`
- [X] T027 [P] [US1] Domain test: wrong code increments attempts and reaching `MAX_VERIFY_ATTEMPTS` invalidates the code in `backend/src/accounts/tests/test_otp_attempts.py`
- [X] T028 [P] [US1] Domain test: crossing `LOCKOUT_THRESHOLD` locks the phone for `LOCKOUT_DURATION_SECONDS` and refuses requests and verifications in `backend/src/accounts/tests/test_lockout.py`
- [X] T029 [P] [US1] Domain test: invalid return URL falls back to `DEFAULT_RETURN_PATH` while a valid allowlisted target is honored in `backend/src/accounts/tests/test_return_url.py`
- [X] T030 [P] [US1] Security test: no log entry contains a full phone number, OTP code, or token across request/verify/refresh/logout in `backend/src/accounts/tests/test_log_masking.py`
- [X] T031 [P] [US1] Frontend component test: login form shows the expiry countdown and the "The code is incorrect" message for wrong/expired codes in `frontend/tests/login-form.test.tsx`

### Implementation for User Story 1

- [X] T032 [P] [US1] Implement the OTP issue service (validate/normalize phone, enforce cooldown `REQUEST_COOLDOWN_SECONDS` and `REQUEST_HOURLY_CAP`, generate a `OTP_LENGTH`-digit code, store HMAC hash with `OTP_TTL_SECONDS`, dispatch via the SMS gateway) in `backend/src/accounts/services.py`
- [X] T033 [P] [US1] Implement the OTP verify service (constant-time hash compare, attempt increment, threshold invalidation, lockout check, implicit user creation, token issuance, return-URL validation) in `backend/src/accounts/services.py`
- [X] T034 [US1] Implement the JWT session service (issue access + refresh, rotate on refresh, blacklist/denylist on logout and on block) using SimpleJWT in `backend/src/accounts/services.py`
- [X] T035 [P] [US1] Implement per-phone and per-source DRF throttle classes (request, verify, global) reading rates from settings/constance in `backend/src/accounts/throttles.py`
- [X] T036 [P] [US1] Implement input/output serializers with Pydantic boundary validation (phone number, code, `return_url`) in `backend/src/accounts/serializers.py`
- [X] T037 [US1] Implement the OTP request, verify, refresh, and logout views in `backend/src/accounts/api.py` with the shared error shape
- [X] T038 [US1] Wire the auth routes (`otp/request`, `otp/verify`, `token/refresh`, `logout`) into `backend/src/accounts/urls.py` and include them from `backend/src/config/urls.py`
- [X] T039 [P] [US1] Implement the typed frontend API client for the auth endpoints in `frontend/src/lib/api/auth.ts`
- [X] T040 [P] [US1] Implement the login page with phone entry, OTP entry, and expiry countdown in `frontend/app/(auth)/login/page.tsx` and `frontend/src/features/auth/`
- [X] T041 [P] [US1] Implement client-side return-URL capture and redirect handling in `frontend/src/features/auth/returnUrl.ts`
- [X] T042 [P] [US1] Implement token storage/handling (access token in memory, refresh via `httpOnly` cookie, CSRF header on state-changing calls) in `frontend/src/lib/session/`
- [X] T043 [US1] Add structured, sampled logging with masked identifiers for OTP requested/succeeded/failed and lockout events in `backend/src/accounts/services.py`
- [X] T044 [US1] Register the `accounts` models in `backend/src/accounts/admin.py` so operators can view users, set `status`, manage `regular`/`admin` groups with django-guardian, and edit constance constants
- [X] T045 [US1] Run `pytest backend/src/accounts/tests` and `yarn test` in `frontend/` and fix failures until the User Story 1 suite is green

**Checkpoint**: User Story 1 is fully functional and independently testable (MVP).

---

## Phase 4: User Story 2 - Guest state is identifiable (Priority: P2)

**Goal**: The system reliably distinguishes a guest from an authenticated user so public
browsing continues and login can be triggered on demand.

**Independent Test**: Load any page while logged out and confirm the session endpoint reports
`authenticated: false, role: "guest"`; log in and confirm it reports the authenticated user
and role.

### Tests for User Story 2 ⚠️

- [X] T046 [P] [US2] Contract test for `GET /api/v1/auth/session` returning the guest shape without a token and the authenticated shape with a valid token in `backend/src/accounts/tests/test_contract_session.py`
- [X] T047 [P] [US2] Domain test: role resolution returns `guest`, `regular`, or `admin` based on session validity and Django group membership (django-guardian) in `backend/src/accounts/tests/test_role_resolution.py`
- [X] T048 [P] [US2] Domain test: a blocked or revoked user is treated as unauthenticated (guest) rather than authenticated in `backend/src/accounts/tests/test_revoked_is_guest.py`
- [X] T049 [P] [US2] Frontend test: the app renders the guest state and prompts login on a protected action, then returns to the originating page in `frontend/tests/guest-state.test.tsx`

### Implementation for User Story 2

- [X] T050 [US2] Implement the session/role resolver in `backend/src/accounts/selectors.py` (returns guest when there is no valid token or the user is blocked/revoked; otherwise the user's group role)
- [X] T051 [US2] Implement `GET /api/v1/auth/session` in `backend/src/accounts/api.py` returning `{authenticated, user{phone, role}}` or `{authenticated: false, role: "guest"}`
- [X] T052 [US2] Expose `get_user_role`/`is_authenticated` through `backend/src/accounts/interfaces.py` for other modules
- [X] T053 [P] [US2] Implement the frontend guest-state signal and login prompt in `frontend/src/lib/session/` and `frontend/src/features/auth/`
- [X] T054 [US2] Run `pytest backend/src/accounts/tests` and `yarn test` in `frontend/` and fix failures until the User Story 2 suite is green

**Checkpoint**: Both user stories work independently; guests are reliably identified.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Hardening and validation that affect the whole feature

- [X] T055 [P] Verify the CORS exact allowlist rejects unknown origins and that no wildcard is configured in `backend/src/config/settings.py`
- [X] T056 [P] Verify CSRF double-submit enforcement on all state-changing auth endpoints in `backend/src/config/settings.py` and `backend/src/accounts/api.py`
- [X] T057 [P] Add rate-limit and DoS behavior tests confirming `429` + `Retry-After` under burst while the service stays responsive in `backend/src/accounts/tests/test_throttling.py`
- [X] T058 [P] Generate the OpenAPI schema with drf-spectacular and confirm it matches `specs/001-sms-otp-login/contracts/auth-api.md`
- [X] T059 [P] Add regression tests for any bug fixed during implementation in `backend/src/accounts/tests/`
- [X] T060 Verify no admin-frontend code was added and that `accounts` is reached only via `accounts/interfaces.py`
- [X] T061 Run the `specs/001-sms-otp-login/quickstart.md` scenarios V1–V12 end to end

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; can start immediately.
- **Foundational (Phase 2)**: Depends on Setup; BLOCKS all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational. MVP.
- **User Story 2 (Phase 4)**: Depends on Foundational; the session resolver (T050) reuses the
  token/session service from US1 (T034), so run US1 first in practice.
- **Polish (Phase 5)**: Depends on the desired user stories being complete.

### Within Each User Story

- Tests are written first and MUST fail before implementation.
- Models/state helpers before services; services before endpoints; backend before frontend
  integration where the frontend depends on the contract.

### Parallel Opportunities

- T004–T007 (Setup), T009–T016 and T020 (Foundational) are parallelizable within their phases.
- All US1 test tasks T022–T031 are parallelizable.
- T032, T033, T035, T036 are parallelizable; T037–T038 follow the services.
- US1 frontend tasks T039–T042 are parallelizable.
- All US2 test tasks T046–T049 are parallelizable.

---

## Parallel Example: User Story 1

```bash
# Tests first (all in parallel):
Task: "Contract test for POST /api/v1/auth/otp/request in backend/src/accounts/tests/test_contract_otp_request.py"
Task: "Contract test for POST /api/v1/auth/otp/verify in backend/src/accounts/tests/test_contract_otp_verify.py"
Task: "Domain test for implicit signup in backend/src/accounts/tests/test_implicit_signup.py"

# Then parallel service work:
Task: "Implement OTP issue service in backend/src/accounts/services.py"
Task: "Implement throttle classes in backend/src/accounts/throttles.py"
Task: "Implement serializers in backend/src/accounts/serializers.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (blocks all stories).
3. Complete Phase 3: User Story 1.
4. STOP and VALIDATE: run the User Story 1 tests and quickstart V1–V10.
5. Deploy/demo if ready.

### Incremental Delivery

1. Setup + Foundational → foundation ready.
2. User Story 1 → test independently → MVP.
3. User Story 2 → test independently → deploy.
4. Polish → hardening and full quickstart validation.

---

## Notes

- [P] tasks touch different files and have no incomplete dependencies.
- Every domain behavior has an automated test (constitution Principle VIII); getters/setters
  and trivial framework tests are intentionally omitted.
- All tunable values are django-constance database constants or `settings.py` values — never
  hard-coded (Principle XIII).
- Roles and permissions use django-guardian; no ad-hoc role flags (Principle XII).
- All models inherit `TimestampedModel` from `backend/src/utils/models.py`.
- The admin panel is a separate restricted-domain application and is out of scope here.
