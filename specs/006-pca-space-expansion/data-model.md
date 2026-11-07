# Phase 1 Data Model: Periodic PCA Space Expansion

No new persisted models and no migrations. Only derived structures change.

## ExpandedPlanSpace (cached)

| Field | Notes |
|---|---|
| `version` | Corpus + semantic-config fingerprint |
| `space` | Existing `PlanSpace` plus a fitted semantic encoder |
| `values` | Explicit dimensions followed by ten semantic dimensions |
| `masks` | Same shape; semantic columns masked for empty titles |
| `ids`, `published_at` | Aligned with rows |

Invariants: `values.shape == masks.shape`; all values finite; column count equals
`len(space.names)`.

## SemanticPlanProfile (derived)

Ten values in `[0, 1]` from `values["plan_name"]` (fallbacks `title`, `name`). Empty
titles use `0.5` with mask `0`.

## PreferenceState (existing, longer vectors)

`InterestProfile.position` and `.uncertainty` gain ten entries. If `space_version` or
length differs from the active space, the existing ranking/signal code rebuilds the state
from the cold-start prior. No migration.

## Configuration

| Setting | Default |
|---|---|
| `RECOMMENDATION_SEMANTIC_DIMENSIONS` | `10` |
| `RECOMMENDATION_SEMANTIC_N_FEATURES` | `1024` |
| `RECOMMENDATION_SEMANTIC_NGRAM_MIN` | `2` |
| `RECOMMENDATION_SEMANTIC_NGRAM_MAX` | `4` |
| `RECOMMENDATION_SEMANTIC_RANDOM_STATE` | `0` |
