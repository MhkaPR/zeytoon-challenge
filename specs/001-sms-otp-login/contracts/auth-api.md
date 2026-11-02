# Contract: Authentication API (v1)

Base path: `/api/v1/auth`. JSON in, JSON out. All timestamps ISO-8601 UTC. Error bodies use
a single shape (below). This contract is the reviewed source of intent; the generated
OpenAPI schema (drf-spectacular) is the machine-readable form.

## Conventions

- Authentication: `Authorization: Bearer <access_token>` on authenticated endpoints.
- CSRF: state-changing requests MUST include `X-CSRFToken` matching the CSRF cookie.
- CORS: only the user-frontend origin(s) from the exact allowlist may call these endpoints.
- Throttling: responses may be `429` with a `Retry-After` header.
- Masking: no response or log includes a full phone number except where the user's own
  number is intentionally echoed back as a masked value.

### Error shape

```json
{
  "error": {
    "code": "otp_incorrect",
    "message": "The code is incorrect",
    "fields": {}
  }
}
```

## POST /otp/request

Request a one-time code for a phone number.

**Request**

```json
{ "phone_number": "09123456789" }
```

**Responses**

| Status | Meaning | Body |
|--------|---------|------|
| 200 | Code created and dispatched | `{ "status": "sent", "expires_in_seconds": 120 }` |
| 400 | Invalid phone number | error `code: "invalid_phone"`, no SMS sent (FR-018) |
| 409 | Blocked user | error `code: "user_blocked"`, `message` = block message, `fields.channels` = contact channels (FR-021) |
| 429 | Rate limited / cooldown / lockout | error `code: "rate_limited"` or `"locked_out"`, `Retry-After` (FR-019, FR-017) |

**Rules**
- The response is `sent` only if a code was actually created and handed to the SMS gateway.
- A new phone number does NOT create the user here; the user is created on first successful
  verification (FR-005).

## POST /otp/verify

Submit the code to complete login.

**Request**

```json
{ "phone_number": "09123456789", "code": "123456", "return_url": "/plans/compare?ids=1,2" }
```

`return_url` is optional; when absent the default page is used.

**Responses**

| Status | Meaning | Body                                                                                                                                                                                                    |
|--------|---------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 200 | Logged in | `{ "access_token": "...", "token_type": "Bearer", "expires_in": 900, "redirect_to": "/plans/compare?ids=1,2", "user": { "phone": "09123456789", "role": "regular" } }` and a `Set-Cookie` refresh token |
| 400 | Wrong, expired, or absent code | error `code: "otp_incorrect"`, `message` = "The code is incorrect" (FR-015)                                                                                                                             |
| 409 | Blocked user | error `code: "user_blocked"`, block message + channels (FR-021)                                                                                                                                         |
| 429 | Too many attempts / locked out | error `code: "too_many_attempts"` or `"locked_out"` (FR-016, FR-017, FR-020)                                                                                                                            |

**Rules**
- Invalid `return_url` never fails the login; `redirect_to` falls back to the default page
  (FR-011).
- On the first success for a new phone, the account is created implicitly (FR-005).
- The response never includes a full phone number.

## POST /token/refresh

Rotate the refresh token and obtain a new access token. Reads the refresh token from the
`httpOnly` cookie; requires the CSRF token.

| Status | Meaning | Body |
|--------|---------|------|
| 200 | Refreshed | new `access_token` + `expires_in`, rotated refresh cookie |
| 401 | Missing/expired/revoked refresh token | error `code: "invalid_token"` |
| 409 | Blocked user | error `code: "user_blocked"` |

## POST /logout

Invalidate the caller's tokens.

| Status | Meaning | Body |
|--------|---------|------|
| 200 | Logged out | `{ "status": "ok" }`; refresh cookie cleared |
| 401 | No valid session | error `code: "not_authenticated"` |

## GET /session

Return the current identity and role, or an explicit guest result.

| Status | Meaning | Body                                                                               |
|--------|---------|------------------------------------------------------------------------------------|
| 200 | Authenticated | `{ "authenticated": true, "role": "regular", "user": { "phone": "09123456789", "role": "regular" } }` |
| 200 | Guest | `{ "authenticated": false, "role": "guest" }`                                      |

This endpoint is the canonical guest-vs-authenticated signal for the frontend (FR-010).

## Cross-cutting behaviors

- **Guest requests**: any request without a valid access token is treated as a guest request
  (FR-010); browsing endpoints are unaffected by this feature.
- **Admin panel**: no endpoint here grants admin-panel access. Admin-panel authentication is
  owned by the separate restricted-domain application (FR-012, FR-013).
- **Rate limiting**: `/otp/request` and `/otp/verify` are throttled per phone and per source,
  plus a global limit to absorb bursts and protect against DoS (FR-019, FR-020).
- **Logging**: every endpoint emits structured JSON logs with masked identifiers (FR-026,
  FR-027).
