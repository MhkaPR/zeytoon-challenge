# Quickstart Validation: SMS OTP Login

A runnable guide to prove the feature works end-to-end. It references
[spec.md](./spec.md), [data-model.md](./data-model.md), and
[contracts/auth-api.md](./contracts/auth-api.md) instead of duplicating their details.

## Prerequisites

- Python 3.14 with the project virtualenv active; dependencies installed.
- PostgreSQL and Redis reachable (locally via Docker; both hosted in Iran per the
  constitution).
- Environment variables set (never committed): `DJANGO_SECRET_KEY`, database URL, Redis URL,
  `SMS_GATEWAY_*` credentials, `JWT_SIGNING_KEY`, and the frontend origins for the CORS
  allowlist.
- Frontend dependencies installed (`yarn` in `frontend/`).
- The `accounts` module created with `python manage.py startapp accounts` and added to
  `INSTALLED_APPS` (Principle XII).

## Setup

```bash
# from repo root
cd backend/src
python manage.py migrate
python manage.py createsuperuser   # operator account for admin-side management
python manage.py runserver 0.0.0.0:8000
```

```bash
# in a second terminal
cd frontend
yarn dev
```

In development, configure the SMS gateway adapter to the console/fake implementation so
codes are visible in the backend log (masked codes are never logged in production).

## Validation Scenarios

### V1 — New user logs in (implicit signup) — proves FR-001..FR-005, FR-011

1. Open the user frontend at `/plans/compare?ids=1,2` while logged out; confirm the app
   treats you as a guest (the session endpoint returns `authenticated: false`).
2. Open the login page; enter a valid, previously unused phone number; request a code.
3. Confirm the response is `sent` with `expires_in_seconds`, and that a countdown appears.
4. Enter the code from the gateway; confirm you are logged in and redirected back to
   `/plans/compare?ids=1,2`.
5. Confirm exactly one user row exists for that normalized phone number.

**Expected**: login succeeds, account created implicitly, return URL honored.

### V2 — Existing user logs in — proves FR-005

1. Log out, then repeat V1 with the same phone number.
2. **Expected**: the same user logs in; no duplicate account is created.

### V3 — Wrong code — proves FR-015, FR-016

1. Request a code, then submit an incorrect value.
2. **Expected**: response is `400` with message exactly "The code is incorrect"; the attempt
   counter increases. Repeat until the configured maximum; the code is then invalidated.

### V4 — Expired code — proves FR-014, FR-015

1. Request a code and wait past `otp_ttl_seconds` (or advance time in tests).
2. Submit the (now expired) code.
3. **Expected**: message is exactly "The code is incorrect"; the system never states that the
   code expired.

### V5 — Temporary lockout — proves FR-016, FR-017

1. Fail verification until the lockout threshold is crossed.
2. Attempt to request a new code and to verify again.
3. **Expected**: both are refused with a "try again later" message until the lockout window
   elapses.

### V6 — Rate limiting / DoS protection — proves FR-019, FR-020, SC-008

1. Request codes for the same phone in quick succession; then repeat rapidly from one source.
2. **Expected**: requests beyond the cooldown/hourly cap and per-source limit return `429`
   with `Retry-After`, while the service stays responsive under burst.

### V7 — Invalid phone number — proves FR-018

1. Submit a malformed or out-of-region number.
2. **Expected**: `400` with `invalid_phone`; no SMS is sent and no code is stored.

### V8 — Blocked user — proves FR-021, SC-003

1. As an operator, set a user's status to `blocked`.
2. Attempt to request a code and to verify.
3. **Expected**: refusal with the message "To resolve the block, contact us through the
   following communication channels" followed by the configured channels.

### V9 — Invalid return URL — proves FR-011, SC-005

1. Complete login while supplying a return target outside the allowlist (e.g. an external
   URL).
2. **Expected**: login still succeeds and the user lands on the configured default page.

### V10 — Token refresh, rotation, and revocation — proves FR-025, FR-029

1. After login, call the refresh endpoint; confirm a new access token and a rotated refresh
   cookie.
2. Log out; confirm the refresh cookie is cleared and the previous tokens are rejected.
3. Block the user as an operator; confirm existing tokens are rejected on next use.

### V11 — Log masking — proves FR-026, FR-027, SC-006

1. Exercise the flows above, then inspect the structured JSON logs.
2. **Expected**: no entry contains a full phone number, a full OTP code, or a token; security
   events (requested, succeeded, failed, locked out, blocked) are recorded with masked IDs.

### V12 — Guest state and configurable values — proves FR-010, FR-030, SC-004

1. Load a public page while logged out; confirm the guest signal.
2. Change a threshold (e.g. `OTP_TTL_SECONDS`) in the django-constance database constants via
   the Django admin and repeat a scenario; confirm the new value takes effect without code
   changes.
3. Grant the `admin` group to a user with django-guardian and confirm role-based checks
   reflect the change.

## Automated Test Entry Points

- Backend: `pytest backend/src/accounts/tests` (unit + API tests for OTP, lockout, JWT,
  masking). Use the fake SMS gateway and time freezing.
- Frontend: `yarn test` in `frontend/` for the login form states and the expiry countdown.

## Success Checklist

- [ ] V1–V12 pass.
- [ ] No `[NEEDS CLARIFICATION]` items remain in the spec.
- [ ] Constitution gates (plan.md) still pass after implementation.
- [ ] No admin-frontend code was added (the admin panel is a separate application).
