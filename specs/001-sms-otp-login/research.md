# Phase 0 Research: SMS OTP Login

All Technical Context unknowns are resolved below. Each entry records the decision, why it
was chosen, and what alternatives were considered.

## R1. Phone number validation and normalization

- **Decision**: Use the `phonenumbers` library to parse, validate, and normalize numbers to
  E.164 before any OTP is created. Reject numbers that fail validation for the configured
  default region.
- **Rationale**: Hand-written regexes are error-prone and cannot track national numbering
  plan changes; `phonenumbers` is the maintained reference implementation (Principle XII).
  Normalizing to E.164 guarantees the "phone number is the unique identifier" rule works
  even when users type local formats.
- **Alternatives considered**: Custom regex per country (rejected: brittle); storing raw
  input (rejected: breaks uniqueness).

## R2. OTP storage and TTL

- **Decision**: Store the hashed OTP in Redis under a key derived from the normalized phone
  number, with the TTL set from settings. Store only a salted hash of the code, never the
  plaintext. The counter for failed attempts lives in the same record.
- **Rationale**: Redis gives native per-key TTL, which implements the required expiry without
  a cleanup job, and satisfies the constitution's mandate that Redis back caching/queues.
- **Alternatives considered**: A Postgres table with an `expires_at` column (rejected: needs
  a sweeper and adds write load on the hot path); plaintext OTP in cache (rejected by
  Principle III).

## R3. Hashing strategy for stored sensitive data

- **Decision**: Hash OTP codes with a fast keyed hash (HMAC-SHA256 with a server-side secret)
  because codes are short-lived and low-entropy; rely on TTL + attempt limits for brute-force
  resistance. Store any other sensitive at-rest fields (e.g. encrypted provider/contact data)
  with an authenticated encryption scheme.
- **Rationale**: OTPs expire in minutes and are rate-limited, so a slow password hash adds
  latency without meaningful benefit; the secret key prevents offline reconstruction.
- **Alternatives considered**: bcrypt/argon2 for OTPs (rejected: latency on the hot path for
  no security gain given TTL and attempt caps); plaintext (rejected by Principle III).

## R4. Session/token strategy

- **Decision**: Issue JWTs via `djangorestframework-simplejwt`: short-lived access token
  (default 15 min) returned to the client and kept in memory, refresh token (default 7 days)
  in an `httpOnly`/`Secure`/`SameSite` cookie, rotated on each refresh. Revocation uses
  SimpleJWT's token denylist (backed by the configured cache) so access/refresh tokens can be
  invalidated on logout or when an operator blocks a user.
- **Rationale**: SimpleJWT is the de-facto Django library for JWT auth, covering rotation and
  denylist out of the box (Principle XII). Keeping the access token in memory mitigates XSS
  token theft.
- **Alternatives considered**: Hand-rolled JWT (rejected: reinventing security-critical code);
  opaque DB sessions (rejected: contradicts Principle XI, which mandates JWT).

## R5. CSRF strategy

- **Decision**: Use Django's CSRF framework with double-submit tokens: the CSRF cookie is
  readable by the frontend and every state-changing request must send a matching
  `X-CSRFToken` header. The refresh cookie is `SameSite=Strict`. Bearer-authenticated
  requests remain subject to CSRF only where a cookie is used.
- **Rationale**: Double-submit is the standard, framework-supported defense for
  cookie-bearing requests and needs no custom middleware.
- **Alternatives considered**: Disabling CSRF for the API (rejected: unsafe with cookies);
  custom token scheme (rejected: needless complexity).

## R6. CORS configuration

- **Decision**: Use `django-cors-headers` with an explicit `CORS_ALLOWED_ORIGINS` allowlist
  read from settings/env, listing the user frontend origin(s) only. `CORS_ALLOW_CREDENTIALS`
  is enabled for the refresh cookie; wildcard origins are rejected.
- **Rationale**: The library is the standard solution and enforces an exact allowlist
  (Principle XII, spec FR-023). The admin frontend origin is intentionally excluded because
  the admin panel is a separate application outside this feature.
- **Alternatives considered**: Manual middleware (rejected); wildcard (rejected by spec).

## R7. Rate limiting and throttling

- **Decision**: Use DRF's throttling framework with cache-backed throttles: a per-phone
  throttle on OTP request, a per-phone throttle on verification, and a per-source
  (IP/user-agent) throttle plus a global anon/user rate. Cooldown and per-window caps are
  read from settings. Temporary lockout after repeated failures is enforced in the service
  layer and recorded in Redis with a TTL.
- **Rationale**: DRF throttling is framework-native and configurable per view; a service-layer
  lockout handles the cross-request "temporary lockout" behavior that throttles alone cannot
  express.
- **Alternatives considered**: Third-party limiter package (rejected: DRF throttling already
  covers it); reverse-proxy-only limiting (rejected: not sufficient alone, though it may be
  layered).

## R8. SMS gateway integration

- **Decision**: Define an `SmsGateway` interface in `accounts/sms.py` with one method to send
  a code, and provide an env-configured implementation plus a fake for tests. The gateway
  choice and credentials come from environment variables.
- **Rationale**: Keeps the domain independent of a specific provider (Principle V),
  satisfies the "secrets only from env" rule (Principle III), and makes tests deterministic.
- **Alternatives considered**: Direct SDK calls in the view (rejected: coupling + untestable);
  a Celery-only send path (deferred: synchronous send is enough for the MVP; the interface
  allows moving to a queue later without changing callers).

## R9. Return-URL validation

- **Decision**: Validate the requested return target against a settings-configured allowlist
  of paths/prefixes on the user frontend origin; anything not matching falls back to the
  configured default page. Never redirect to an absolute external URL supplied by the client.
- **Rationale**: Prevents open-redirect abuse while honoring the "return to the same page"
  requirement (spec FR-011).
- **Alternatives considered**: Accepting any relative path (rejected: still allows crafted
  paths); accepting absolute URLs (rejected: open redirect).

## R10. Observability and log masking

- **Decision**: Emit structured JSON logs at the four required levels and a logging filter
  that masks phone numbers (keep a short prefix/suffix) and redacts OTP codes and tokens.
  Record counters for OTP requested, verification succeeded/failed, lockout triggered, and
  block refusal. Hot paths (throttle rejections) are aggregated/sampled.
- **Rationale**: Satisfies Principle VII and spec FR-026/FR-027 without flooding logs.
- **Alternatives considered**: Logging full identifiers (rejected by spec); unstructured
  logs (rejected by Principle VII).

## R11. Testing approach

- **Decision**: pytest + pytest-django for the backend with a fake SMS gateway, Redis test
  instance, and `freezegun` for TTL/expiry and lockout timing; Next.js component tests for
  the login form states and countdown.
- **Rationale**: Enables deterministic tests of time-dependent behavior, which this feature
  depends on heavily (Principle VIII: test domain behavior, not trivia).
- **Alternatives considered**: Django `unittest` only (viable but more boilerplate);
  mocking time via sleeps (rejected: slow and flaky).

## R12. API contract documentation

- **Decision**: Generate the OpenAPI schema with `drf-spectacular` and keep the hand-written
  contract in `contracts/` as the reviewed source of intent.
- **Rationale**: Gives consumers an accurate, generated schema while keeping a
  review-friendly contract in the repo (Principle XII).
- **Alternatives considered**: Hand-maintained schema (rejected: drifts); no schema
  (rejected: poor consumer experience).
