# Phase 1 Data Model: Periodic PCA Space Expansion

**Feature**: `006-pca-space-expansion`
**Date**: 2026-11-07

This feature introduces **no new persisted models and no migrations**. It extends the
derived recommendation structures introduced by feature 005 and reuses the existing
`InterestProfile` and `InterestSignal` tables.

## SemanticPlanProfile (derived, in memory)

The ten-component semantic representation of one published plan.

| Attribute | Type | Rules |
|---|---|---|
| `semantic_0` … `semantic_9` | float in `[0, 1]` | Principal component scores mapped linearly from the fitted corpus. Exactly `RECOMMENDATION_SEMANTIC_DIMENSIONS` values (default 10). |
| `semantic_mask` | float `0` or `1` | `1` when the plan has a non-empty title; `0` when the title is empty or missing. |

**Source**: `values["plan_name"]`, falling back to `values["title"]` or `values["name"]`.

**Validation rules**

- Values are finite and clipped to `[0, 1]`.
- Empty titles receive neutral `0.5` with mask `0` (FR-012).
- When the corpus has fewer plans than dimensions, missing components are neutral `0.5`.

## ExpandedPlanSpace (derived, cached in Redis)

The bundle returned by `PlanSpaceProvider` and consumed by ranking and signal recording.

| Field | Type | Rules |
|---|---|---|
| `version` | string | Corpus + semantic configuration fingerprint (FR-007). |
| `space` | fitted `PlanSpace` | Contains numeric binners, categorical vocabularies, and the fitted semantic encoder. |
| `values` | 2-D float array | One row per plan; explicit dimensions followed by semantic dimensions. |
| `masks` | 2-D float array | Same shape as `values`; semantic columns masked when the title is empty. |
| `ids` | list of integers | Plan ids aligned with rows. |
| `published_at` | list of strings | Publish timestamps aligned with rows. |
| `semantic_dimensions` | integer | Number of semantic columns appended. |
| `semantic_metadata` | object | n-gram range, hash size, random state, fitted component count, and scaling bounds. |

**Invariants**

- `values.shape == masks.shape`.
- `values.shape[1] == len(space.names) == explicit_dimensions + semantic_dimensions`.
- `len(ids) == len(published_at) == values.shape[0]`.
- All values are finite.

## PreferenceState (existing, extended shape)

Stored on `InterestProfile.position` and `InterestProfile.uncertainty`.

| Field | Change | Rules |
|---|---|---|
| `position` | Length grows by the semantic dimension count | One value per active space dimension, each in `[0, 1]`. |
| `uncertainty` | Length grows by the semantic dimension count | Same length as `position`, each `>= 0`. |
| `space_version` | Unchanged | Must equal the active space version for the stored state to be used. |

**Reconciliation rule**

```text
profile.space_version == active.version AND len(profile.position) == active_dimensions
    -> use stored position and uncertainty
otherwise
    -> rebuild from the cold-start prior with full uncertainty
```

Reconciliation never changes `user`, `visitor_id`, `merged_into`, or any other profile's
data (FR-009, FR-010).

## RecalculationRun (derived, not persisted)

One scheduled refresh, represented by cache keys and structured logs.

| Attribute | Type | Rules |
|---|---|---|
| `last_run_at` | cache timestamp | Updated only after a successful swap; drives the due check. |
| `lock` | cache key | `recommendations:space:refresh:lock`, TTL configurable, prevents overlap. |
| `active_key` | cache key | `recommendations:space:active`, points at the current bundle key. |

**State transitions**

```text
due check passes
    -> acquire lock
    -> fit semantic encoder and expanded space
    -> validate bundle
    -> write versioned bundle
    -> update active pointer
    -> update last_run_at
    -> release lock

any failure or invalid bundle
    -> log error
    -> leave active pointer and last_run_at unchanged
    -> release lock
```

## Relationships

- One `ExpandedPlanSpace` is shared by all viewers.
- One `InterestProfile` has one `PreferenceState` aligned with the active
  `ExpandedPlanSpace` version.
- `InterestSignal` rows are unchanged and continue to feed `PreferenceState` updates.

## Configuration

| Setting | Default | Purpose |
|---|---|---|
| `RECOMMENDATION_SEMANTIC_DIMENSIONS` | `10` | Number of semantic dimensions appended. |
| `RECOMMENDATION_SEMANTIC_N_FEATURES` | `1024` | Hashing vector size. |
| `RECOMMENDATION_SEMANTIC_NGRAM_MIN` | `2` | Minimum character n-gram. |
| `RECOMMENDATION_SEMANTIC_NGRAM_MAX` | `4` | Maximum character n-gram. |
| `RECOMMENDATION_SEMANTIC_RANDOM_STATE` | `0` | PCA determinism seed. |
| `RECOMMENDATION_SPACE_REFRESH_INTERVAL_HOURS` | `24` | Minimum interval between refreshes. |
| `RECOMMENDATION_SPACE_REFRESH_LOCK_TTL` | `900` | Refresh lock lifetime in seconds. |
