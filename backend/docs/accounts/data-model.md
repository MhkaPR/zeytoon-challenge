# accounts — Data Model

## User

Table: `accounts_user`

| Column | Type | Notes |
|---|---|---|
| `id` | bigint | primary key |
| `username` | varchar | required by `AbstractUser`; defaults to phone |
| `phone_number` | varchar(32) | normalized E.164; unique among active rows |
| `password` | varchar | unusable password marker for OTP users |
| `status` | varchar(16) | `active` / `blocked` |
| `is_active` | bool | Django active flag; blocked or inactive users are guests |
| `is_staff` / `is_superuser` | bool | Django admin flags |
| `last_login` | timestamp | updated by SimpleJWT |
| `created_at` / `updated_at` | timestamp | inherited |
| `deleted_at` | timestamp | soft delete |

Constraints:

- `uniq_active_user_phone`: unique `phone_number` where `deleted_at IS NULL`.

Relationships:

- groups and permissions from Django auth;
- object permissions from django-guardian;
- companies, verification decisions, credit entries, and interest profiles reference this
  user from their own apps.

## Roles

Roles are not a column. They are Django groups:

| Group | Capability |
|---|---|
| `regular` | normal authenticated user |
| `ops` | `/api/v1/ops/` operator console |
| `admin` | ops console plus Django admin |

`ensure_role_groups()` creates the groups; migration `0003_create_ops_role_group` seeds
them.

## Cache keys (not database rows)

| Key | TTL | Purpose |
|---|---|---|
| `otp:{phone}` | `OTP_TTL_SECONDS` | hashed code, attempts, expiry |
| `otp:lockout:{phone}` | `LOCKOUT_DURATION_SECONDS` | temporary lockout |
| `otp:failures:{phone}` | `LOCKOUT_DURATION_SECONDS` | rolling failure count |
| `otp:source:{ip}:{ua}` | 1 hour | per-source request counter |

## Migrations

| Migration | Change |
|---|---|
| `0001_initial` | user model |
| `0002_unusable_password_for_otp_users` | unusable passwords |
| `0003_create_ops_role_group` | ops group |
| `0004_remove_user_email` | remove email |
| `0005_alter_user_managers_user_deleted_at` | soft delete |
| `0006_alter_user_phone_number_user_uniq_active_user_phone` | active-phone uniqueness |
| `0007_alter_user_managers` | manager update |
