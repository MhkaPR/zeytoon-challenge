# accounts — Architecture

## 1. Responsibility

`apps.accounts` owns identity for the whole backend:

- the custom phone-based user model;
- role resolution (`regular`, `ops`, `admin`);
- SMS OTP request/verification;
- JWT access/refresh token issuance and revocation;
- guest/authenticated session resolution;
- OTP throttling, lockout, and return-URL safety;
- the SMS gateway abstraction.

It is the only app allowed to define the user model or issue tokens.

## 2. Internal layout

| Path | Responsibility |
|---|---|
| `models/user.py` | `User`, `UserManager`, role helpers, phone normalization, unusable password |
| `validation.py` | E.164 phone normalization/validation via `phonenumbers` |
| `state.py` | Redis/cache-backed OTP payloads, attempt counters, lockouts, source counters |
| `sms.py` | `SmsGateway` interface plus console, capturing, and HTTP placeholders |
| `throttles.py` | per-phone and per-source DRF throttle classes |
| `selectors.py` | Bearer-token caller resolution and guest identity |
| `services/v1/accounts.py` | OTP request/verify, token issue/revoke, return-URL resolution |
| `serializers/v1/accounts.py` | input/output serializers |
| `views/v1/accounts.py` | authentication ViewSets and refresh-cookie handling |
| `exceptions.py` | `ApiError` and the shared API exception handler |
| `interfaces.py` | `AccountsInterface` for other apps |
| `urls.py` | `/api/v1/auth/` routes |

## 3. User model

`User(AbstractUser, TimestampedModel)`:

- `phone_number` is the unique login identifier for active rows.
- `username` is retained because `AbstractUser` requires it; it defaults to the normalized
  phone number.
- `email` is removed (`email = None`).
- `status` is `active` or `blocked`.
- Passwords are always unusable for OTP users (`set_unusable_password()`), so
  `has_usable_password()` is false.
- A partial unique constraint `uniq_active_user_phone` applies only when
  `deleted_at IS NULL`, allowing re-registration after soft delete.
- `role()` resolves `admin` > `ops` > `regular` from group membership; Django superusers
  are always `admin`.

`UserManager` combines Django's user helpers with the project's soft-delete manager.

## 4. OTP state

OTP state is intentionally **not** stored in the database. It lives in the configured
cache (Redis in real environments) with explicit expiry:

| Key | Value |
|---|---|
| `otp:{phone}` | `{code_hash, attempts, expires_at}` |
| `otp:lockout:{phone}` | lockout marker |
| `otp:failures:{phone}` | rolling failed-verification count |
| `otp:source:{ip}:{ua}` | per-source counter |

Codes are stored as HMAC-SHA256 hashes keyed by `OTP_HASH_SECRET`. Expiry is stored inside
the payload so the implementation works with any Django cache backend.

## 5. Tokens and cookies

- Access token lifetime: `JWT_ACCESS_MINUTES` (default 15 minutes).
- Refresh token lifetime: `JWT_REFRESH_DAYS` (default 7 days).
- `ROTATE_REFRESH_TOKENS` and `BLACKLIST_AFTER_ROTATION` are enabled.
- The refresh token is returned only as an `httpOnly`, `SameSite=Strict`, `Secure`
  (outside DEBUG) cookie scoped to `/api/v1/auth/`.
- Logout blacklists the refresh token and clears the cookie.

## 6. Authorization

- `selectors.user_from_request()` parses the Bearer access token and returns `None` for
  guests, invalid tokens, blocked users, or inactive users.
- `resolve_current_user()` returns an explicit guest result
  (`{"authenticated": false, "role": "guest"}`), so the frontend never infers identity.
- Other apps use `AccountsInterface` or the selectors; they do not read the user table
  directly.

## 7. Dependencies

- `phonenumbers` for validation.
- `djangorestframework-simplejwt` for tokens and blacklist.
- `django-guardian` for object permissions.
- `django-constance` for OTP and return-URL tunables.
- `apps.recommendations.interfaces` for visitor-profile merge/clear on login/logout.
