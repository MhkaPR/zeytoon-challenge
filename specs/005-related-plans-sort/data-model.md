# Phase 1 Data Model: Personalized Related Plans Ordering

**Feature**: `005-related-plans-sort`
**Date**: 2026-11-06

Two persisted models live in the new `apps.recommendations` application. One derived
structure (the fitted plan space) is cached in Redis, and one value object (the plan
attribute profile) is produced in memory during ranking.

All persisted models inherit the shared `TimestampedModel` from `apps/utils` (soft
delete via `SoftDeleteManager` / `DeletedObjectsManager`, `created_at`, `updated_at`,
`deleted_at`) and are registered with `django-auditlog`, per `backend-rules.md` and the
constitution.

## InterestProfile

The accumulated preference of one viewer. Exactly one owner link is set: an anonymous
device (`visitor_id`) or an account (`user`).

| Field | Type | Rules |
|---|---|---|
| `id` | bigint PK | Surrogate key. |
| `user` | FK to the user model, nullable | Set for account-scoped profiles. Unique among active rows. |
| `visitor_id` | UUID, nullable | Opaque random device identifier from the visitor cookie. Unique among active rows. |
| `position` | JSON (list of floats) | Preference position in the plan space, one value per dimension in `[0, 1]`. |
| `uncertainty` | JSON (list of floats) | Per-dimension uncertainty, same length as `position`; `>= 0`. |
| `space_version` | string | Version of the plan space the position was produced against. A mismatch triggers a re-fit on next read. |
| `signal_count` | positive integer | Number of signals absorbed; used for bounded influence and diagnostics. |
| `last_signal_at` | datetime, nullable | Timestamp of the most recent absorbed signal; drives ageing/decay and retention expiry. |
| `merged_into` | FK to the user model, nullable | Tombstone: set when a device profile is folded into an account. |
| `created_at` / `updated_at` / `deleted_at` | datetime | From `TimestampedModel`. |

**Constraints**

- Constraint `one_owner`: exactly one of `user` / `visitor_id` is non-null.
- Partial unique index on `user` where `deleted_at IS NULL`.
- Partial unique index on `visitor_id` where `deleted_at IS NULL`.
- Index on `last_signal_at` for retention sweeps.
- `position` and `uncertainty` lengths must match the active `space_version`; a mismatch
  is treated as an empty profile rather than an error.

**Relationships**

- One `InterestProfile` has many `InterestSignal` rows.
- A device `InterestProfile` may point at an account through `merged_into`.

**State transitions**

```text
(none) --first signal--> anonymous profile (visitor_id)
account login, no account profile, device profile present
    -> account profile created from device position; device profile tombstoned (merged_into=account)
account login, account profile present
    -> account profile kept; device profile tombstoned (merged_into=account)
sign-out
    -> device profile contents cleared and device profile soft-deleted; account profile untouched
inactivity beyond retention
    -> profile soft-deleted by the retention sweep
```

**Validation rules (from the spec)**

- A visitor identity is never chosen by the client for merge purposes (FR-009).
- A device profile is never shared with more than one account (FR-008, FR-022).
- Tombstoned device profiles redirect late signals to `merged_into` instead of absorbing
  them (edge case: signal around sign-in).

## InterestSignal

An append-only record of one interaction attributed to one profile. Retained for the
profile retention window and used for diagnostics, decay, and future offline evaluation.

| Field | Type | Rules |
|---|---|---|
| `id` | bigint PK | Surrogate key. |
| `profile` | FK to `InterestProfile` | The profile that absorbed the signal. Required. |
| `kind` | string (choices) | One of `destination_visit`, `details_view`, `search_impression`. |
| `plan_ids` | JSON (list of integers) | Candidate plan ids the signal refers to. One id for a click/view; many for a search impression. |
| `query` | string, nullable | The typed query, only for `search_impression`. Never contains personal data beyond what the visitor typed. |
| `weight` | float | The measurement noise applied, copied from the configured signal weights at recording time. |
| `created_at` / `updated_at` / `deleted_at` | datetime | From `TimestampedModel`. |

**Constraints**

- Index on `(profile, created_at)` for recent-signal lookups and retention sweeps.
- Index on `kind` for diagnostics.
- `plan_ids` must be non-empty for every kind; `query` is required only for
  `search_impression`.

**Relationships**

- Many `InterestSignal` rows belong to one `InterestProfile`.

## PlanAttributeProfile (derived, in memory)

The comparable attributes of one published plan, produced by `PlanFeatureMapper` during
ranking. Not persisted; cached only as part of the fitted plan space.

| Attribute | Source (aliases, via catalog normalization) |
|---|---|
| `price` | `price_amount`, `price` |
| `cpu` | `vcpu_cores`, `cpu_cores`, `cpu` |
| `ram` | `ram_amount`, `ram` |
| `disk` | `storage_amount`, `disk_amount`, `disk` |
| `traffic` | `traffic_amount`, `bandwidth_amount`, `traffic`, `bandwidth` |
| `country` | `location`, `datacenter_location` |
| `os` | `os`, `operating_system` |

**Rules**

- Each dimension carries an existence mask; a missing attribute is masked and excluded
  from distance (FR-016).
- Numeric values are normalised to `[0, 1]` by the space's binner; categorical values are
  one-hot within a dimension-specific mask.
- A plan with every dimension masked is never ranked above a plan with comparable
  declared attributes; it falls back to the cold-start tie-break order.

## PlanSpaceCache (derived, Redis)

The fitted plan space for the current catalogue version.

| Key | Value | TTL |
|---|---|---|
| `recommendations:space:v1:<catalog_version>` | Serialised bin edges, category lists, dimension names, and the plan-id → vector index. | Until the catalogue version changes, capped at a configured maximum. |

**Rules**

- The catalogue version is derived from published records (latest publish timestamp and
  count) so a publish naturally invalidates the cache (FR: new plans eligible).
- A cache miss rebuilds the space from `PublishedRecord` rows and warms the key.
- Redis is only a cache; losing it degrades performance, never correctness.

## SortSelection (not persisted)

The viewer's current ordering choice for one catalogue request.

| Value | Meaning | Applies to |
|---|---|---|
| `related` | Related order using the viewer's profile (default). | Main catalog, company catalog. |
| `price` | Ascending price (existing behaviour). | Main catalog, company catalog, search. |
| `expensive` | Descending price (existing behaviour). | Main catalog, company catalog, search. |

**Rules**

- Omitted or default → `related` on the main and company catalogs.
- Search results default to query relevance and expose only `price` / `expensive`
  (FR-015, FR-021).
