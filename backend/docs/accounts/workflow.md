# accounts — Workflow

## 1. Request an OTP

`POST /api/v1/auth/otp/request`

```text
normalize_phone(raw)
  → invalid: ApiError(invalid_phone)
  → state.is_locked_out(phone): ApiError(locked_out, 429, retry_after_seconds)
  → existing blocked user: ApiError(user_blocked, 409, channels)
  → generate_code() using OTP_LENGTH
  → store_code() with OTP_TTL_SECONDS
  → get_gateway().send_code(phone, code)
  → return {status: "sent", expires_in_seconds}
```

The response always reports `sent`; it does not reveal whether an account already exists.

## 2. Verify an OTP

`POST /api/v1/auth/otp/verify`

```text
normalize_phone(raw)
  → reject invalid phone / lockout / blocked user
  → read cached code payload
      absent or expired → register failed attempt → otp_incorrect
  → compare HMAC hash with hmac.compare_digest
      mismatch → increment attempts
                 if attempts >= MAX_VERIFY_ATTEMPTS: delete code + force lockout
                 else register failed attempt
                 → otp_incorrect
  → success: delete code, clear lockout
  → transaction:
      get_or_create User(phone_number=phone, username=phone)
      if visitor_id cookie: RecommendationsInterface.merge_on_login(user, visitor_id)
  → issue_tokens(user)
  → resolve_return_url(return_url)
  → set refresh cookie
```

New phone numbers are created implicitly; there is no separate signup endpoint.

## 3. Failed-attempt and lockout behavior

- `MAX_VERIFY_ATTEMPTS` invalidates the active code after repeated wrong guesses.
- `LOCKOUT_THRESHOLD` failed attempts trigger `set_lockout()` for
  `LOCKOUT_DURATION_SECONDS`.
- A lockout blocks both request and verify until it expires.
- A successful verification clears both the lockout and the failure counter.

## 4. Refresh a session

`POST /api/v1/auth/token/refresh`

```text
read refresh_token cookie
  → missing: invalid_token 401
  → parse RefreshToken
  → if rotation enabled:
      blacklist old refresh
      load user; missing/blocked → user_blocked 409
      issue new refresh
  → return new access token and set new refresh cookie
```

Refresh is not treated as an OTP action and does not consume the per-source OTP budget.

## 5. Resolve the current session

`GET /api/v1/auth/session`

```text
Bearer token absent/invalid/blocked → {authenticated: false, role: "guest"}
valid user                          → {authenticated: true, role, user: {phone, role}}
```

## 6. Logout

`POST /api/v1/auth/logout`

```text
blacklist refresh cookie token (best effort)
RecommendationsInterface.clear_visitor(visitor_id)
delete refresh_token cookie
delete visitor_id cookie
return {status: "ok"}
```

## 7. Return-URL safety

`resolve_return_url(return_url)`:

- rejects absolute URLs and protocol-relative targets;
- requires a path beginning with `/`;
- accepts only paths matching `RETURN_URL_ALLOWLIST` (exact or prefix);
- falls back to `DEFAULT_RETURN_PATH`.

This prevents open redirects after login.

## 8. Throttling

| Throttle | Scope | Key |
|---|---|---|
| `OtpRequestPhoneThrottle` | `otp_request_phone` | phone number |
| `OtpVerifyPhoneThrottle` | `otp_verify_phone` | phone number, window from constance |
| `OtpSourceThrottle` | `otp_source` | client IP + user agent |

Global `anon` and `user` throttles also apply through DRF defaults.
