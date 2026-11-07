# Phase 0 Research: Periodic PCA Space Expansion

**Feature**: `006-pca-space-expansion`
**Date**: 2026-11-07

## 1. Semantic algorithm and library

**Decision**: Use `sklearn.feature_extraction.text.HashingVectorizer` with
`analyzer="char_wb"`, `ngram_range=(2, 4)`, `n_features=2**10`,
`alternate_sign=False`, `norm="l2"`, followed by `sklearn.decomposition.PCA` with a
fixed `random_state`, exactly as prototyped in `pca.py`. Add `scikit-learn` to the
backend dependencies.

**Rationale**: The prototype is the user's stated algorithm. Both estimators are
maintained, widely adopted, and deterministic when seeded; this satisfies Constitution
XII instead of hand-rolling hashing and SVD.

**Alternatives considered**:
- Hand-rolled hashing + numpy SVD — rejected: duplicates mature library behaviour and
  violates Principle XII.
- Sentence embeddings / LLM summaries — rejected: adds external cost, latency, and a
  model dependency for a demo-scale catalogue.
- TF-IDF vocabulary — rejected: the prototype deliberately uses fixed-size hashing so
  the space does not need a persisted vocabulary.

## 2. Mapping PCA output into `[0, 1]`

**Decision**: After fitting, record each component's minimum and maximum over the
training corpus and map component scores linearly into `[0, 1]`, clipping at the edges.
Store the mapping inside the fitted encoder in the cached bundle. A missing or empty
title receives the neutral value `0.5` with mask `0`.

**Rationale**: The existing `PlanSpace` and `UserState` assume every dimension lives in
`[0, 1]`. Min-max scaling preserves relative distances and keeps the Kalman update
comparable with explicit dimensions. Neutral-with-mask avoids penalising plans whose
titles carry no signal (FR-012).

**Alternatives considered**:
- Rank/quantile scaling — rejected: ties and corpus changes make it less stable.
- Raw PCA scores — rejected: negative and unbounded values break the existing distance
  and Kalman assumptions.

## 3. Small or degenerate corpora

**Decision**: Fit `n_components = min(configured_dimensions, n_samples, n_features)`.
Pad any missing semantic dimensions with `0.5` and mask `1` for non-empty titles. If the
corpus is empty, skip the swap and keep the previous space.

**Rationale**: Satisfies FR-019 and the edge cases for empty/single-plan catalogues
without failing the refresh.

**Alternatives considered**:
- Raise on small corpora — rejected: would break small catalogues and violate FR-019.
- Duplicate rows to reach the dimension count — rejected: fabricates signal.

## 4. Space versioning

**Decision**: Compute the version from a fingerprint of the published corpus: the count,
the latest `published_at`, a hash of the ordered `(id, title)` pairs, and the semantic
configuration (dimension count, n-gram range, hash size, random state). Any change to
plans or configuration produces a new version.

**Rationale**: Satisfies FR-007 and prevents stale semantic components from being served
after titles or configuration change.

**Alternatives considered**:
- Count + latest timestamp only — rejected: a title edit without a publish timestamp
  change would not invalidate the space.
- Random UUID per refresh — rejected: breaks deterministic cold start and cache reuse.

## 5. Atomic swap and last-known-good

**Decision**: Keep the existing versioned bundle key and add an active-pointer key
`recommendations:space:active` holding the bundle key. A refresh writes the new bundle
first, validates it, then updates the pointer in one `cache.set`. Readers resolve the
pointer and verify its version against the current corpus fingerprint; a mismatch falls
back to on-demand fitting so correctness is preserved.

**Rationale**: Satisfies FR-006 and FR-013. Readers never see a partial bundle, and a
failed refresh leaves the pointer on the previous complete space.

**Alternatives considered**:
- Write only the versioned key — rejected: a failed refresh would be silently bypassed
  by on-demand fitting and the previous space would not be guaranteed.
- Two-phase database transaction — rejected: the space lives in Redis, not PostgreSQL.

## 6. Periodic scheduling

**Decision**: Add a `@task` body `refresh_plan_space_task` and a management command
`refresh_recommendation_space`. The command checks a cache timestamp against the
configured interval and enqueues the task only when due. Production scheduling invokes
the command from the existing external scheduler pattern (cron/systemd timer), mirroring
`run_scheduled_replays`.

**Rationale**: Django Tasks has no built-in periodic scheduler in this project; the
existing convention is a management command enqueuing work. The interval remains
configurable and the command is idempotent.

**Alternatives considered**:
- A long-running scheduler process — rejected: new operational component.
- Celery beat — rejected: Celery is forbidden by `backend-rules.md`.
- Enqueue on every catalogue request — rejected: violates the periodic requirement and
  adds hot-path work.

## 7. Concurrency and overlapping runs

**Decision**: Acquire `recommendations:space:refresh:lock` with `cache.add` and a
configurable TTL before fitting. If the lock is held, log a skipped run and return.
Release the lock in a `finally` block.

**Rationale**: Satisfies FR-015 without a new queue or database table.

**Alternatives considered**:
- Database advisory lock — rejected: unnecessary for a cache-resident artifact.
- No lock — rejected: overlapping fits can race the pointer update.

## 8. Preference-state reconciliation

**Decision**: Keep the existing rule: when a profile's `space_version` differs from the
active version or its vector length differs from the active dimension count, rebuild the
state from the cold-start prior with full uncertainty. Preserve viewer identity and never
copy values between profiles.

**Rationale**: Satisfies FR-009 and FR-010 with the simplest safe behaviour. The
explicit-attribute layout can change when categorical vocabularies change, so preserving
a prefix is not always safe.

**Alternatives considered**:
- Preserve matching prefix dimensions — rejected: unsafe when category vocabularies
  shift positions.
- Migrate stored profiles in a data migration — rejected: unnecessary; reconciliation on
  read is deterministic and avoids a migration.

## 9. Validation and failure handling

**Decision**: Before swapping, validate that the bundle has the expected number of
dimensions, finite values, matching mask shape, and at least one plan. On any exception
or validation failure, log a structured error and leave the active pointer unchanged.

**Rationale**: Satisfies FR-013 and FR-014 and prevents corrupt spaces from reaching
ranking.

**Alternatives considered**:
- Trust the fit output — rejected: silent NaN/Inf would corrupt ordering.
- Roll back by restoring the old key — rejected: the old key is never removed.

## 10. Observability

**Decision**: Emit structured JSON logs with event names
`recommendation_space_refresh_started`, `..._succeeded`, `..._skipped`, and
`..._failed`, including version, plan count, dimension count, duration, and error class.
Refresh runs are low-frequency, so no sampling is needed.

**Rationale**: Satisfies Principle VII and FR-014 without log spam.

## 11. Dependency and test impact

**Decision**: Add `scikit-learn` to `pyproject.toml` and install with `uv sync`. Tests
use the locmem cache from `config.settings.test`, so no Redis is required in CI.

**Rationale**: Keeps the existing test setup unchanged and exercises the same code paths.

**Alternatives considered**:
- Require Redis in tests — rejected: slower and unnecessary.
