# Phase 0 Research: Intent-Pattern Recommendation Explanations

## R1 — Pattern registry shape and extensibility

**Decision**: Represent each pattern as a small immutable definition carrying a stable key,
a predicate over a normalized feature view, a fallback flag, and a mapping of direction to
Persian copy. Keep a single `INTENT_PATTERNS` ordered mapping with exactly the five keys
`cheap`, `value`, `spec_heavy`, `premium`, and `exploring`. Scoring iterates only the four
entries whose fallback flag is false.

**Rationale**: Adding a pattern becomes a registry entry, satisfying the open/closed
requirement. Keeping `exploring` in the registry makes the approved key set explicit while
the fallback flag guarantees it is never scored.

**Alternatives considered**: Separate real/fallback registries (two sources of truth);
if/elif scoring branches (violates the extensibility requirement).

## R2 — Normalized feature view

**Decision**: Build a per-plan feature view from the loaded space using dimension names:
`price_pct` from the `price` dimension, `cpu_pct`, `ram_pct`, and `disk_pct` from their
dimensions, and `spec_pct` as the mean of the present `ram_pct`, `cpu_pct`, and `disk_pct`
values. A missing dimension is excluded from the mean; a pattern that needs a missing
dimension does not match. `traffic_pct` is not part of `spec_pct` because the specification
defines the resource intent around RAM, CPU, and disk.

**Rationale**: The space already stores normalized values and existence masks. Using masks
prevents a missing attribute from being treated as zero. The definition keeps `value`,
`premium`, and `spec_heavy` consistent with one another.

**Alternatives considered**: Treating missing values as zero (biases patterns toward
incomplete plans); including traffic in `spec_pct` (changes the stated intent semantics);
re-binning raw values (duplicates the space and risks drift).

## R3 — Contingency table and gate order

**Decision**: For each real pattern and cluster, use the candidate set `R` of row indices
and the pattern membership set `S_P` over the full catalog. Compute `TP = |R ∩ S_P|`,
`FP = |S_P| - TP`, `FN = |R| - TP`, and `TN = N - |R| - FP`. Apply gates in order: minimum
pattern size (`TP + FP`), two-sided Fisher Exact (`p <= alpha`), Lift
(`(TP / (TP + FP)) / (|R| / N) >= min_lift`), then absolute MCC (`>= min_mcc`). Rank
survivors by `Lift × |MCC|`.

**Rationale**: The gate order cheaply rejects tiny patterns before the Fisher test and
matches the specification. Using the actual candidate-set size `|R|` rather than the
configured `K` keeps Lift correct when the catalog is smaller than `K`.

**Alternatives considered**: Using configured `K` in the denominator (overstates Lift for
small catalogs); ranking by Fisher p-value alone (ignores effect size).

## R4 — Fisher Exact and MCC implementations

**Decision**: Use `scipy.stats.fisher_exact` with `alternative="two-sided"` for Gate 2.
Declare SciPy explicitly in `pyproject.toml` because it is now a direct dependency even
though scikit-learn already installs it transitively. Use the canonical MCC formula with
explicit zero-denominator handling that returns `0.0`.

**Rationale**: SciPy is already an installed transitive dependency of scikit-learn and is
the established library for Fisher Exact. MCC has no maintained count-based helper that
avoids materializing full label arrays; the formula is short, exact, and guarded. This is a
documented exception to the library-first rule justified by avoiding O(N) temporary arrays
per pattern.

**Alternatives considered**: `sklearn.metrics.matthews_corrcoef` with expanded arrays
(allocates arrays of length N for every pattern/cluster); hand-written Fisher Exact
(forbidden by the constitution).

## R5 — Signal corroboration and cluster attribution

**Decision**: Treat the existing `destination_visit` signal as the outbound click. Load the
viewer's destination-visit signals once per request, expand their `plan_ids`, map each
clicked plan to its space row, and attribute it to the cluster whose position is nearest to
the plan vector. For a cluster, require at least `RECOMMENDATION_EXPLAIN_MIN_CLICKS`
attributed clicks with usable normalized values, then apply the pattern-specific mean
thresholds. Missing price/spec values are skipped.

**Rationale**: Signals are stored against plans, not clusters, so nearest-cluster
attribution is the only way to corroborate per-cluster intent without changing feature-005
signal capture. Reusing `destination_visit` avoids a new signal kind or migration.

**Alternatives considered**: Adding an `outbound_click` signal kind (changes feature-005
scope and frontend capture); corroborating against all clicks regardless of cluster
(defeats per-cluster independence).

## R6 — Direction and negative MCC

**Decision**: Report `direction = "positive"` when MCC is positive and `"negative"` when
MCC is negative. Corroboration always checks the pattern's positive behavioral signature,
as specified. Add `RECOMMENDATION_EXPLAIN_NEGATIVE_ENABLED`; when false, reject every
negative-direction pattern. Negative copy uses question-form "avoiding" phrasing from the
configurable message catalog.

**Rationale**: The product owner wants an operational switch for negative intents. Keeping
corroboration positive avoids inventing inverse thresholds that are not in scope.

**Alternatives considered**: Inverting corroboration for negative MCC (adds unspecified
thresholds and changes acceptance behavior).

## R7 — Per-cluster display

**Decision**: Return every cluster explanation in cluster order and render one UI section
per explanation. Do not count or rank intents across clusters. Repeated intents are
merged into one section so the same reason is not shown twice.

**Rationale**: The viewer should see each distinct reason once. Showing `value` twice
makes the suggestion strip look repetitive and pushes other reasons out of view.

**Alternatives considered**: Primary-intent counting (rejected by the product owner);
keeping repeated intents as separate sections (rejected as repetitive).

## R8 — Where copy lives

**Decision**: Store every question-form message in the django-constance message catalog.
Backend service modules contain no Persian strings. The API returns the configured
`message` per explanation, and the frontend renders each section's message as response
data.

**Rationale**: Operators can change copy without a deploy, and service code stays
language-neutral. The API contract still provides ready-to-render text.

**Alternatives considered**: Hardcoded Persian in the registry (violates the product
owner's instruction); frontend-only copy (diverges from the required API message).

## R9 — Removal of feature-based explanations

**Decision**: Delete `services/v1/reasons.py`, `serializers/v1/reasons.py`, the old
frontend explanation formatter/badge, and the old feature-explanation tests. Rename the
ranking entry point to `suggest_with_explanations`. Remove obsolete constance keys
(`PERCENTILE_LO`, `PERCENTILE_HI`, `F1_THRESHOLD`, `TOP_N`) and keep `EXPLAIN_K`.

**Rationale**: One source of truth and no dead code. The persisted explanation model is
already removed by migration `0006`; no new migration is needed.

**Alternatives considered**: Leaving the old code behind a flag (dead code and drift risk).

## R10 — Determinism

**Decision**: Use stable pattern order, stable cluster order, deterministic candidate
ordering from the existing recommender, fixed rounding for confidence values, and the
documented tie-break. No wall-clock, random, or request-order input enters the result.

**Rationale**: Satisfies byte-identical output for the same profile and space version.

**Alternatives considered**: Randomizing the primary intent for variety (breaks
determinism and user trust).

## R11 — Performance

**Decision**: Compute pattern membership masks once per request with vectorized NumPy
operations, reuse them across clusters, and perform at most four Fisher tests per cluster.
Load destination-visit signals once. Do not rebuild or re-persist the space.

**Rationale**: The work is O(N × 4) plus a constant number of statistical tests, well
within the existing 100 RPS read-heavy target. The only new database query is the signal
history for the viewer.

**Alternatives considered**: Recomputing pattern membership per cluster (wasteful);
caching pattern masks in Redis (premature; the space is already cached and the masks are
cheap).
