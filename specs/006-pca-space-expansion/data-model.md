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

## PreferenceState (existing, now multi-cluster)

`InterestProfile.position` is a list of cluster vectors; `.uncertainty` is the matching
list of uncertainty vectors. Each cluster has one value per active space dimension. A
flat list of numbers is read as a single cluster for backward compatibility.

Signals update the nearest cluster when its distance is at most
`RECOMMENDATION_CLUSTER_DISTANCE_THRESHOLD`; otherwise a new cluster is created. At
`RECOMMENDATION_MAX_INTEREST_CLUSTERS` the least confident cluster is evicted. Ranking
uses the minimum distance across clusters. If `space_version` or any vector length
differs from the active space, the profile is rebuilt from the cold-start prior. No
migration.

## Configuration

| Setting | Default |
|---|---|
| `RECOMMENDATION_SEMANTIC_DIMENSIONS` | `10` |
| `RECOMMENDATION_SEMANTIC_N_FEATURES` | `1024` |
| `RECOMMENDATION_SEMANTIC_NGRAM_MIN` | `2` |
| `RECOMMENDATION_SEMANTIC_NGRAM_MAX` | `4` |
| `RECOMMENDATION_SEMANTIC_RANDOM_STATE` | `0` |
| `RECOMMENDATION_MAX_INTEREST_CLUSTERS` | `4` |
| `RECOMMENDATION_CLUSTER_DISTANCE_THRESHOLD` | `0.2` |
