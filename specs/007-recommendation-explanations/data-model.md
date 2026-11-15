# Phase 1 Data Model: Recommendation Explanations

This feature **adds persisted models and a migration**. Recommendation state moves to
PostgreSQL as the source of truth: a `RecommendationSpace` model holds the fitted plan
space, and a `RecommendationExplanation` model holds each viewer's computed explanations.
Redis becomes a read-through cache in front of them. Computed read-time objects
(`FeatureGroup`, `FeatureMatch`, `ClusterExplanation`) remain in-memory and feed the
persisted explanation payload. `NumericBinner` gains observed min/max (no storage impact
beyond the persisted space row).

## Existing entities reused

### InterestProfile (`apps/recommendations/models/interest_profile.py`)

- `position`: list of cluster vectors (or one flat legacy vector), each with one normalized
  value per space dimension.
- `uncertainty`: matching list of uncertainty vectors.
- `space_version`: version string of the space the position was built against.
- Owner: exactly one of `user` or `visitor_id`.
- **No change** to fields or constraints.

### PlanSpace bundle (persisted in PostgreSQL; cached in Redis at `recommendations:space:v1:<version>`)

- `values`, `masks`: `[0, 1]` matrices, one row per published plan.
- `ids`, `published_at`: row-aligned plan identity/time.
- `space`: fitted `PlanSpace` with `names` (dimension order), numeric `binners`,
  `categories`, and the semantic encoder.
- **Additive change**: `NumericBinner` gains `min`/`max` of observed values so a normalized
  position can be reverted and clamped. Scaling output is unchanged.

## New persisted entities

Both inherit the shared timestamped base model (`apps/utils`), use the custom soft-delete
manager, and are registered with `auditlog`, per `backend-rules.md` §6.

### RecommendationSpace (`apps/recommendations/models/recommendation_space.py`)

The durable home of the fitted space; Redis is a cache derived from it.

| Field | Type | Meaning | Validation |
|-------|------|---------|------------|
| `version` | string (unique, indexed) | Space version string from `PlanSpace.version()` | Non-empty; unique |
| `names` | JSON | Ordered dimension names | Length equals vector width |
| `values` | JSON | Serialized plan vector matrix | Finite values |
| `masks` | JSON | Serialized existence masks | Same shape as `values` |
| `scales` | JSON | Numeric min/max/edges and categorical vocabularies | Required to revert values |
| `plan_ids` | JSON | Row-aligned published plan ids | Same length as `values` |
| `published_at` | JSON | Row-aligned timestamps | Same length as `values` |
| `is_active` | bool | The currently served version | Exactly one active row |
| `plan_count` | int | Number of plans fitted | Non-negative |

Rules:

- A refresh writes a new row, flips `is_active`, and invalidates the Redis key
  (spec FR-019, FR-021, FR-022).
- Readers fall back to the active DB row when the cache is cold; they never silently serve a
  non-active version.
- Failed rebuilds MUST NOT replace the active row (mirrors feature 006 FR-008).

### RecommendationExplanation (`apps/recommendations/models/recommendation_explanation.py`)

The durable per-viewer explanation result, keyed by space version.

| Field | Type | Meaning | Validation |
|-------|------|---------|------------|
| `profile` | FK → `InterestProfile` | Owning viewer profile | Required |
| `space_version` | string | Version the payload was computed against | Must match active version to be served |
| `payload` | JSON | Serialized list of `ClusterExplanation` | Bounded by cluster cap |
| `computed_at` | datetime | When the payload was produced | Auto |

Rules:

- Written on first computation for a `(profile, space_version)` pair; re-read on later calls
  (spec FR-020).
- A row whose `space_version` is stale is recomputed, not served (spec FR-022, FR-015).
- Rows follow the existing interest-profile retention window (180 days of inactivity).

## New computed objects (not persisted)

### FeatureGroup

One logical feature used to explain a match.

| Field | Meaning | Validation |
|-------|---------|------------|
| `key` | Stable dimension identity, e.g. `semantic` or `cpu` | Non-empty; drawn from `PlanSpace.names` |
| `category` | `textual` or `technical` | Enum; exactly two categories |
| `kind` | `textual`, `technical_numeric`, or `technical_categorical` | Enum |
| `closeness` | Ranking score in `[0, 1]` (higher = closer) | Finite; used only for ordering |
| `label` | Dimension label (numeric) or category name (categorical/textual) | Non-empty |

Rules:

- The ten `semantic_*` dimensions collapse into a **single** `textual` FeatureGroup.
- Each technical dimension (`price`, `cpu`, `ram`, `disk`, `traffic`, and
  `<field>=<value>`) is its own FeatureGroup.
- `has_*` presence columns are excluded from explainable groups.
- Groups masked out for the chosen plan are excluded.

### FeatureMatch (reverted, user-facing)

One selected FeatureGroup after reverting normalization.

| Field | Meaning | Validation |
|-------|---------|------------|
| `category` | `textual` / `technical` | From the group |
| `kind` | As above | From the group |
| `name` | Attribute name for numeric technical (`cpu`, `ram`, ...) | Present for numeric |
| `unit` | Real unit (`core`, `GB`, `IRR`, ...) | Present for numeric when known |
| `low`, `high` | Approximate real-value range around the reverted value | `low <= high`; within `[min, max]` |
| `label` | Category name for textual/categorical | Present for those kinds |

Rules (from spec FR-006..FR-014):

- At most the configured number of matches (default 3) per explanation.
- Numeric technical matches quote a range widened by the configured range width and clamped
  to the observed catalogue min/max.
- Categorical and textual matches never expose numbers.
- Missing plan attributes are omitted, not zeroed.

### ClusterExplanation

One explanation for one interest cluster.

| Field | Meaning | Validation |
|-------|---------|------------|
| `plan_id` | Closest published plan id for this cluster | Must exist in the space bundle |
| `matches` | Ordered list of `FeatureMatch` | 0..configured count |
| `has_textual` | Whether a textual match was selected | Derived |

Rules (from spec FR-001..FR-015):

- One `ClusterExplanation` per retained cluster; total never exceeds
  `RECOMMENDATION_MAX_INTEREST_CLUSTERS`.
- Deduplicated by `plan_id`; duplicate clusters keep the closer cluster's matches.
- A cluster still on the cold-start prior yields no explanation.
- Outdated/incompatible profiles yield no explanation, never an error.

### ExplanationSet

The response payload: the ordered list of `ClusterExplanation` plus, for each, the closest
plan's public fields needed to render it. See `contracts/explanations.md`.

## State transitions

- **No interest → interest**: cold-start prior produces no explanation; after real signals
  clusters exist and explanations appear.
- **Cluster replaced** (cap reached): the surviving clusters' explanations remain; the
  replaced cluster's explanation disappears.
- **Space version change**: positions that no longer match yield no explanation until
  rebuilt; requests keep succeeding.

## Configuration (Constitution XIII)

Added to `CONSTANCE_CONFIG` / `conf.py`:

- `RECOMMENDATION_EXPLANATION_FEATURE_COUNT` (int, default 3) — max named features.
- `RECOMMENDATION_EXPLANATION_RANGE_WIDTH` (float, default 0.1) — fraction of a numeric
  dimension's observed span added around the reverted value.

Reused existing keys: `RECOMMENDATION_MAX_INTEREST_CLUSTERS`,
`RECOMMENDATION_SEMANTIC_DIMENSIONS`, `RECOMMENDATION_N_BINS`.

## Migration

A single new migration in `apps/recommendations/migrations/` creates the
`RecommendationSpace` and `RecommendationExplanation` tables. No data migration is needed:
existing `InterestProfile` rows keep working, and the space is rebuilt and persisted on the
next refresh. Migration files are generated with `makemigrations` and are never hand-edited
(`backend-rules.md` §6).
