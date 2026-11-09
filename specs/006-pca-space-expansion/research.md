# Phase 0 Research: Periodic PCA Space Expansion

## 1. Algorithm and library

**Decision**: Use `HashingVectorizer(analyzer="char_wb", ngram_range=(2, 4),
n_features=2**10, alternate_sign=False, norm="l2")` and `PCA(random_state=0)`, matching
`pca.py`. Add `scikit-learn` as a dependency.

**Rationale**: Same algorithm the user prototyped; satisfies Principle XII.

**Alternatives**: Hand-rolled numpy SVD (rejected: duplicates a library), embeddings
(rejected: external cost).

## 2. Scaling to `[0, 1]`

**Decision**: Min-max scale each PCA component using bounds recorded from the fitted
corpus, clipped to `[0, 1]`. Empty titles get `0.5` with mask `0`.

**Rationale**: The existing distance and Kalman update assume `[0, 1]`.

**Alternatives**: Raw PCA scores (rejected: negative/unbounded), rank scaling (rejected:
less stable).

## 3. Small corpora

**Decision**: Fit `min(configured_dimensions, n_samples, n_features)` components and pad
missing dimensions with `0.5`. Skip the refresh if there are no plans.

**Rationale**: Handles empty and tiny catalogues without errors.

## 4. Versioning

**Decision**: Include plan count, latest publish time, a hash of `(id, title)` pairs, and
the semantic configuration in the version string.

**Rationale**: A title edit or config change invalidates the cache.

## 5. Scheduled refresh

**Decision**: A `@task` body fits and caches the space. A management command enqueues
it. An external scheduler (cron/systemd timer) calls the command daily by default.

**Rationale**: Follows the existing `run_scheduled_replays` pattern and the Django Tasks
gate. No new scheduler process.

**Alternatives**: Celery beat (forbidden), long-running scheduler (extra component).

## 6. Failure and reconciliation

**Decision**: Fit and validate before writing the cache key, so a failure leaves the old
key intact. Keep the existing rule: a profile with a mismatched version or dimension
count is rebuilt from the cold-start prior.

**Rationale**: Simple, safe, and requires no changes to ranking or signals.

**Alternatives**: Active-pointer swap (rejected: unnecessary complexity), data migration
(rejected: read-time rebuild is enough).
