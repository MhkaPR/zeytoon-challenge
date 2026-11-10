# Phase 1 Data Model: Intent-Pattern Recommendation Explanations

This feature introduces **no persisted models and no migrations**. All intent state is
derived per request from the existing recommendation space, interest profile, and signals.
The only durable data reused are `InterestProfile`, `InterestSignal`, and
`RecommendationSpace`.

## Existing entities reused

### RecommendationSpace bundle

Loaded through `PlanSpaceProvider` (PostgreSQL source of truth, Redis cache).

| Field | Meaning |
|-------|---------|
| `values` | `[0, 1]` normalized matrix, one row per catalog plan |
| `masks` | Existence masks aligned with `values` |
| `ids` | Row-aligned plan ids |
| `published_at` | Row-aligned timestamps for deterministic ordering |
| `space.names` | Dimension order; used to locate `price`, `cpu`, `ram`, `disk` |

### InterestProfile

- `position`: one or more cluster vectors.
- `uncertainty`: matching cluster uncertainty vectors.
- `space_version`: version the profile was built against.
- `signal_count`: used to short-circuit cold-start viewers to `exploring`.
- No field changes.

### InterestSignal

- `kind`: `destination_visit` is treated as the outbound click for corroboration.
- `plan_ids`: clicked plans attributed to the nearest cluster.
- `created_at`: existing ordering.
- No field changes.

## Computed objects (not persisted)

### PlanIntentFeatures

One normalized feature view per catalog row.

| Field | Type | Meaning |
|-------|------|---------|
| `price_pct` | float or absent | Normalized price dimension |
| `cpu_pct` | float or absent | Normalized CPU dimension |
| `ram_pct` | float or absent | Normalized RAM dimension |
| `disk_pct` | float or absent | Normalized disk dimension |
| `spec_pct` | float or absent | Mean of present RAM/CPU/disk values |

Rules:

- A dimension is absent when its mask is zero.
- `spec_pct` is absent when none of RAM, CPU, or disk is present.
- Values are read from the loaded space; raw catalog values are not used.

### IntentPattern

| Field | Type | Meaning |
|-------|------|---------|
| `key` | string | One of `cheap`, `value`, `spec_heavy`, `premium`, `exploring` |
| `matches` | callable | Predicate over `PlanIntentFeatures` |
| `fallback` | bool | True only for `exploring` |
| `messages` | mapping | Direction (`positive`/`negative`) to configured question copy |

Registry rules:

- Exactly five keys.
- `exploring` is never scored.
- No `text_specific` or keyword pattern.
- No Persian strings live in the registry; messages resolve from constance.
- Adding a pattern requires only a new registry entry.

### ContingencyTable

| Field | Meaning |
|-------|---------|
| `tp` | Pattern members inside the candidate set |
| `fp` | Pattern members outside the candidate set |
| `fn` | Candidate-set members outside the pattern |
| `tn` | Catalog members outside both |
| `pattern_size` | `tp + fp` |
| `candidate_size` | `tp + fn` |
| `catalog_size` | `tp + fp + fn + tn` |

Validation:

- All counts are non-negative.
- `catalog_size > 0`.
- Zero denominators in Lift or MCC produce a rejected pattern rather than an exception.

### IntentScore

| Field | Type | Meaning |
|-------|------|---------|
| `key` | string | Real pattern key |
| `lift` | float | Effect size |
| `p_value` | float | Two-sided Fisher Exact result |
| `mcc` | float | Matthews Correlation Coefficient |
| `score` | float | `lift * abs(mcc)` |
| `direction` | `positive` or `negative` | MCC sign |

### ClusterIntentExplanation

| Field | Type | Meaning |
|-------|------|---------|
| `cluster_id` | int | Cluster index |
| `representative_plan_id` | int or null | Closest plan in the cluster's candidate set |
| `plan_ids` | list[int] | Suggested plans assigned to this cluster |
| `intent` | string | Winning real pattern or `exploring` |
| `direction` | string or null | `positive`, `negative`, or null for `exploring` |
| `message` | string | Persian explanation |
| `confidence` | object or null | `{lift, p, mcc}` for real intents; null for `exploring` |

The API returns the full `ClusterIntentExplanation` list in cluster order. Repeated
intents are not deduplicated and there is no primary or aggregate explanation.

## State transitions

None. Explanations are computed and discarded per request. The recommendation space and
profile lifecycle remain owned by features 005 and 006.
