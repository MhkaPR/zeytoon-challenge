# Phase 1 Data Model: SMS OTP Login

Entities and rules derived from spec.md. Field types are indicative, not prescriptive of
exact column types. Per Principle V, only the `accounts` module may touch these tables;
other modules use `accounts/interfaces.py`.

## Shared base: TimestampedModel (`utils` app)

All persistent models in this feature MUST inherit from an abstract `TimestampedModel`
defined once in a shared `utils` app (`backend/src/utils/models.py`), created with
`python manage.py startapp utils`. The base provides the audit timestamps so they are never
re-declared per model (Principle XII, DRY).

```python
class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
```

- Every concrete model below inherits `TimestampedModel`; `created_at`/`updated_at` are not
  listed again in their field tables.
- The `utils` app MUST NOT depend on any domain module; it is a leaf shared by all modules
  (Principle V).

## Permissions: django-guardian

Authorization is managed with **django-guardian**, not a hand-rolled role column.

- Django `Group`s are used for the global roles: a `regular` group and an `admin` group
  (spec FR-009). A user's role is the group they belong to; `guest` is simply the absence of
  an authenticated session.
- Object-level permissions (for example, granting a specific operator rights over a specific
  provider or resource as the platform grows) are assigned with django-guardian's
  `assign_perm`/`get_objects_for_user` APIs and its `GuardianUserObjectPermission` /
  `GuardianGroupObjectPermission` tables.
- Role checks in code MUST go through django-guardian / Django's permission framework
  (or the `accounts/interfaces.py` helpers), never through ad-hoc boolean flags.
- `django-guardian` and its `guardian` app MUST be added to `INSTALLED_APPS` and its
  anonymous-user support enabled in settings.

## User

Represents a person identified by phone number. Backed by Django's auth user so JWT and
django-guardian permissions integrate cleanly; extends it rather than replacing it. Inherits
`TimestampedModel`.

| Field | Notes |
|-------|-------|
| id | Primary key. |
| phone_number | Unique. Normalized to E.164. The user's unique identifier (spec FR-005). |
| status | One of `active`, `blocked`. Default `active`. |
| is_active | Django auth flag; a blocked user is still stored but cannot log in (FR-021). |
| groups | Django groups `regular` / `admin`; the user's role (FR-009). Managed via django-guardian / Django admin. |
| created_at / updated_at | Inherited from `TimestampedModel`. |

**Validation rules**
- `phone_number` MUST be a valid, normalized number; invalid input is rejected before any
  code is created (FR-018).
- `phone_number` MUST be unique; a request for an existing number logs in that user, a new
  number creates the user implicitly (FR-005).

**State transitions**
- `active → blocked` when an operator blocks the account; blocked users are refused at OTP
  request and verification (FR-021).
- `blocked → active` when an operator unblocks. No account deletion transition exists (FR-028).
- Role transitions (`regular` ↔ `admin`) are group-membership changes performed with
  django-guardian; they are outside the login flow (spec Assumptions).

## OneTimeCode

The short-lived challenge bound to a phone number.

| Field | Notes |
|-------|-------|
| key | Redis key derived from the normalized phone number (e.g. `otp:{phone}`). |
| code_hash | HMAC-SHA256 of the code with a server-side secret; plaintext is never stored (FR-022). |
| attempts | Failed-verification counter for this code. |
| issued_at | Issue time, used for the request cooldown. |
| expires_at / ttl | TTL from settings; the user frontend shows a countdown (FR-014). |

**Validation rules**
- At most one active code per phone; issuing a new code replaces the previous one.
- Verification is refused once `attempts` reaches the configured maximum; the code is then
  invalidated (FR-016).
- An expired or absent code produces exactly the message "The code is incorrect" (FR-015).

**State transitions**
- `issued → consumed` on successful verification (the key is deleted).
- `issued → invalidated` on reaching the attempt threshold or expiry.

## LoginAttempt / Lockout

Cross-request counters used to enforce thresholds and temporary lockout.

> Stored in Redis with a TTL (not a database model), so it does not inherit `TimestampedModel`.

| Field | Notes |
|-------|-------|
| phone_number | Subject of the counter (normalized). |
| source | Requester source (IP and/or user-agent fingerprint). |
| failed_count | Failed verifications within the window. |
| window_started_at | Start of the current counting window. |
| locked_until | Set when the lockout threshold is crossed; empty otherwise. |

**Validation rules**
- Reaching the failed-attempt threshold sets `locked_until` for the configured duration
  (FR-017); during lockout, requests and verifications for that phone are refused with a
  "try again later" message.
- Counters are stored in Redis with a TTL equal to the relevant window or lockout.

## Runtime configuration: django-constance (database constants)

There is **no `AuthSettings` model**. Runtime-adjustable values are database-backed constants
managed with **django-constance** (`constance.backends.database.DatabaseBackend`), so
operators can change them from the Django admin without a deploy (Principle XIII, spec
FR-030). The values are declared in `CONSTANCE_CONFIG` in `settings.py` and stored in the
constance database table; code reads them through `constance.config` / the `constance`
template/context or the `CONSTANCE_ADDITIONAL_FIELDS` admin UI.

| Constant | Default | Purpose |
|----------|---------|---------|
| OTP_LENGTH | 6 | Number of digits in the code. |
| OTP_TTL_SECONDS | 120 | Code validity window. |
| MAX_VERIFY_ATTEMPTS | 5 | Failed attempts per code before invalidation. |
| LOCKOUT_THRESHOLD | 5 | Failed attempts before temporary lockout. |
| LOCKOUT_DURATION_SECONDS | 900 | Lockout length. |
| REQUEST_COOLDOWN_SECONDS | 60 | Minimum gap between code requests per phone. |
| REQUEST_HOURLY_CAP | 5 | Max code requests per phone per hour. |
| VERIFY_WINDOW_LIMIT | 10 | Max verifications per phone per window. |
| VERIFY_WINDOW_SECONDS | 600 | Verification window length. |
| CONTACT_CHANNELS | list | Channels shown to a blocked user (FR-021). |
| RETURN_URL_ALLOWLIST | list | Allowed return targets (FR-011). |
| DEFAULT_RETURN_PATH | `/` | Fallback page when the return target is invalid. |

**Notes**
- Constance is configured with the database backend so constants are stored in a Django model
  table, which keeps them consistent with Principle XIII ("Django settings or Django models").
- Settings that must not change at runtime (e.g. JWT lifetimes, CORS allowlist, the JWT
  signing key) stay in `settings.py` and are environment-driven, per FR-030.
- Values shown as defaults are the documented defaults from the spec's Assumptions section.

## Session / Token

The authenticated credential issued after successful verification.

| Field | Notes |
|-------|-------|
| access_token | JWT, default 15-minute lifetime. Returned in the response body. |
| refresh_token | JWT, default 7-day lifetime, rotated on each refresh. Sent as an `httpOnly` cookie. |
| jti | Token identifier, used for denylist revocation on logout or block. |

**Validation rules**
- A revoked `jti` MUST be rejected even before natural expiry (FR-025).
- Logging out invalidates the user's tokens (FR-029).

## Contact Channels

The operator-configured list of communication channels shown to a blocked user
(spec FR-021). Stored as the `CONTACT_CHANNELS` constance constant; rendered as part of the
block message.

## Relationships

- `User` 1—* `OneTimeCode` (only one active at a time, keyed by phone).
- `User` 1—* `LoginAttempt` (by phone and source).
- `User` 1—* `Session/Token` (denylist entries keyed by `jti`).
- `User` *—* Django `Group` (roles `regular` / `admin`), with django-guardian managing
  permission assignment.
- Constance constants are standalone key/value entries consumed by services, not related by
  foreign key.

## Out of Scope (explicitly)

- No profile, registration, or recovery entities.
- No admin-panel access entities or provider-supplied admin UI (FR-012, FR-013).
- No account-deletion or account-merging entities (FR-028).
