# Phase 0 Research: Recommendation Explanations

All technical unknown points in the plan are resolved below. No `NEEDS CLARIFICATION`
markers remain.

## R1 — How to split plan-space dimensions into two feature categories

**Decision**: Classify each dimension by its name in `PlanSpace.names`.

- **Textual/lexical category**: dimensions named `semantic_*` (the ten title-derived PCA
  components, feature 006). All of them are scored together as **one** feature group.
- **Technical specification category**: the remaining dimensions — `price`, `cpu`, `ram`,
  `disk`, `traffic`, and categorical one-hot columns named `<field>=<value>`
  (`country=...`, `os=...`). Each is scored individually. Presence-indicator columns
  (`has_*`) participate in the underlying distance but are **not** eligible to be named,
  because they carry no real value to quote.

**Rationale**: `PlanSpace.names` already enumerates dimensions in a stable order and
already distinguishes semantic columns from explicit attributes, so classification needs no
new model and stays in sync with the space version.

**Alternatives considered**: Hard-coding index ranges (fragile against
`RECOMMENDATION_SEMANTIC_DIMENSIONS`); a separate dimension-metadata table (new
persistence, rejected by Constitution XIII/V).

## R2 — How to pick the "three closest features"

**Decision**: For each interest cluster, take that cluster's closest plan using the existing
`InterestClusters`/`Recommender` machinery. Then, on the chosen plan, compute a per-feature
closeness as `1 - |viewer_position - plan_value|` under the existing masks, where the
textual group uses the masked mean across all ten semantic dimensions and each technical
dimension is scored on its own. Rank features by closeness (descending); keep the top three,
excluding features the plan masks out. Ties break by dimension name for determinism.

**Rationale**: Reuses the same normalized, masked space that ranking already uses, so the
reason describes the same geometry the viewer was ranked by. Aggregating the semantic
dimensions into one score matches the requirement that all ten textual dimensions be
evaluated together.

**Alternatives considered**: Selecting features by global variance (ignores the viewer);
per-dimension semantic scoring (contradicts the "all ten together" requirement).

## R3 — How to revert a normalized value to an approximate real value and range

**Decision**: Extend the existing `NumericBinner` to retain the observed `min` and `max`
alongside its `edges` (an additive, backward-compatible change; existing scaling output is
unchanged). Revert a normalized position `x` on a numeric dimension to the bin whose
interval contains `x * n_bins`, then quote a small range widened by the configurable
`RECOMMENDATION_EXPLANATION_RANGE_WIDTH`, clamped to `[min, max]`. Categorical dimensions
are described by their category name (the `<field>=<value>` label), never as a numeric
range. Dimensions whose plan value is missing are omitted.

**Rationale**: Binner edges are quantile boundaries in the real unit, so the containing
interval already approximates the viewer's real interest; min/max enable clamping. This
avoids storing raw catalog values on the space.

**Alternatives considered**: Storing raw plan values on the space bundle (memory cost, no
benefit); linear min–max reversal (the space is quantile-scaled, so linear reversal would be
wrong).

## R4 — Determinism

**Decision**: Given identical viewer position, cluster set, plan space, and configuration,
the explanation(s) and quoted ranges MUST be byte-identical. Achieved by: stable dimension
ordering from `PlanSpace.names`, deterministic tie-breaking by name, no randomness, no
wall-clock or request-order input, and rounding ranges to a fixed precision.

**Rationale**: Constitution VI and spec FR-013/SC-005 require repeatable output; PCA already
fits with a fixed `random_state`.

**Alternatives considered**: Randomising top-feature choice for variety (rejected —
non-deterministic, breaks SC-005).

## R5 — Where the explanation is produced and delivered

**Decision**: The backend returns a **structured** explanation per cluster — a list of
feature tokens that each carry `kind` (`textual` | `technical_numeric` |
`technical_categorical`), the dimension label, and an optional real-unit range — plus the
closest plan id. The frontend composes the localized sentence from the existing next-intl
catalogue. A new read-only endpoint under the recommendations module returns this; the
suggested-plans surface consumes it. No new persistence.

**Rationale**: Keeping the phrasing in the i18n catalogues satisfies FR-012 (Persian-first,
localized copy) and keeps the backend free of presentation strings, while the backend still
owns the numeric reversal and determinism.

**Alternatives considered**: Backend-rendered prose (duplicates i18n ownership, harder to
localize); frontend-only computation (frontend cannot revert quantile-normalized values
without the space).

## R5b — Persistence of the space and explanations (PostgreSQL, not Redis)

**Decision**: Move recommendation state to PostgreSQL as the source of truth and keep Redis
as a read-through cache only.

- Add a **`RecommendationSpace`** model: `version` (unique, indexed), `names` (dimension
  order), `values`/`masks` payload, numeric min/max/edges per dimension, categorical
  vocabularies, plan count, and an `is_active` flag. One active row per version.
- Add a **`RecommendationExplanation`** model: `profile` FK (or `visitor_id`), `space_version`,
  `payload` (the structured explanations), and audit timestamps.
- `PlanSpaceProvider.load` becomes **read-through**: Redis → DB (active version) → build +
  persist. Redis writes stay the fast path; DB writes happen on refresh/rebuild.
- `refresh` writes a new `RecommendationSpace` row, marks it active, and invalidates the
  Redis cache key.
- Explanations are written to the DB on first computation for a (profile, version) and read
  back on subsequent calls; a version mismatch recomputes.

**Rationale**: The user requires durability: losing Redis must not lose the space or the
explanations. PostgreSQL is already the declared source of truth (Constitution V) and is
Iran-hosted (IV). Redis remains a cache for the hot read path.

**Alternatives considered**: Continuing cache-only (rejected — eviction loses state);
storing as files/objects (rejected — bypasses the source of truth); a separate datastore
(rejected — Constitution V, Data Governance).

## R6 — Configuration

**Decision**: Add two runtime tunables through `apps/recommendations/conf.py` +
`CONSTANCE_CONFIG`, alongside the existing `RECOMMENDATION_*` keys:
`RECOMMENDATION_EXPLANATION_FEATURE_COUNT` (default 3) and
`RECOMMENDATION_EXPLANATION_RANGE_WIDTH` (default a small fraction, e.g. 0.1 of the
dimension's observed span). Both are database-backed via django-constance.

**Rationale**: Constitution XIII forbids hard-coded tunables; the recommendation `conf`
module is the established resolution order (constance → settings → default).

**Alternatives considered**: Settings-only (fails the runtime-adjustable requirement);
hard-coded constants (forbidden).

_(Persistence tunables for the space/explanation retention are added in R5b and the data
model; the explanation feature count and range width remain as above.)_

## R7 — Cluster scope and caps

**Decision**: Produce exactly one explanation per retained interest cluster and never more
than `RECOMMENDATION_MAX_INTEREST_CLUSTERS`; when two clusters resolve to the same closest
plan, emit it once using the closer cluster's reason. A cluster still holding the cold-start
prior (no real signal) yields no explanation.

**Rationale**: Matches FR-002/FR-010 and keeps the payload bounded and non-redundant.

**Alternatives considered**: One explanation per distinct plan across all clusters with
merged reasons (harder to attribute, breaks "per interest" wording).
