# accounts — API

Base path: `/api/v1/auth`

All errors use the shared shape:

```json
{"error": {"code": "...", "message": "...", "fields": {}}}
```

## Endpoints

### `POST /otp/request`

Request a one-time code.

```json
{"phone_number": "09121234567"}
```

Response `200`:

```json
{"status": "sent", "expires_in_seconds": 120}
```

Possible errors: `invalid_phone`, `locked_out` (`429`), `user_blocked` (`409`),
`rate_limited` (`429`).

### `POST /otp/verify`

Verify a code and create a session.

```json
{
  "phone_number": "09121234567",
  "code": "123456",
  "return_url": "/panel"
}
```

Response `200`:

```json
{
  "access_token": "...",
  "token_type": "Bearer",
  "expires_in": 900,
  "redirect_to": "/panel",
  "user": {"phone": "091212***4567", "role": "regular"}
}
```

The refresh token is set as a cookie, never in the JSON body.

Possible errors: `invalid_phone`, `locked_out`, `user_blocked`, `otp_incorrect`,
`rate_limited`.

### `POST /token/refresh`

No request body. Reads the `refresh_token` cookie.

Response `200`:

```json
{"access_token": "...", "token_type": "Bearer", "expires_in": 900}
```

Possible errors: `invalid_token` (`401`), `user_blocked` (`409`).

### `GET /session`

Response `200` for a guest:

```json
{"authenticated": false, "role": "guest"}
```

Response `200` for an authenticated user:

```json
{
  "authenticated": true,
  "role": "regular",
  "user": {"phone": "09121234567", "role": "regular"}
}
```

### `POST /logout`

No request body. Revokes the refresh token and clears cookies.

```json
{"status": "ok"}
```

## Cookies

| Cookie | Scope | Flags |
|---|---|---|
| `refresh_token` | `/api/v1/auth/` | `httpOnly`, `SameSite=Strict`, `Secure` outside DEBUG |
| `visitor_id` | `/` | anonymous recommendation identity, managed by the frontend |

## Roles

| Role | Meaning |
|---|---|
| `guest` | no valid access token |
| `regular` | authenticated user without operator groups |
| `ops` | operator console access |
| `admin` | operator console plus Django admin |
