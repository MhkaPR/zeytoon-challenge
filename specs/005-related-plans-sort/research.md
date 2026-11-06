# Phase 0 Research: Personalized Related Plans Ordering

**Feature**: `005-related-plans-sort`
**Date**: 2026-11-06

All technical unknown values from the plan's Technical Context were resolved during
planning. This file records each decision, its rationale, and the alternatives that were
rejected.

## 1. Preference model

**Decision**: Port the discretized-space model from `kalman_user_intent_detector.py`
into `apps.recommendations` as `PlanSpace` + `UserState`. Each plan is a point in a
normalised attribute space with an existence mask; each viewer profile carries a
position and a per-dimension uncertainty updated by a Kalman-style gain when a signal
arrives. Distances are computed only over dimensions the candidate plan declares.

**Rationale**: It supports a deterministic cold-start prior, graded signal strengths,
per-attribute uncertainty, and cheap in-process updates — exactly the spec's FR-002,
FR-005, FR-007, FR-016, and FR-020. It already exists as a working prototype, reducing
risk.

**Alternatives considered**:
- Popularity/recency order — rejected: cannot be per-viewer (FR-002) or graded (FR-005).
- Collaborative filtering (ALS/implicit/LightFM) — rejected: needs an interaction
  matrix that anonymous first visits do not have, adds a training pipeline, and cannot
  produce the required deterministic cold-start order.
- Simple additive counters per attribute — rejected: no uncertainty, no bounded
  cumulative influence (FR-007), and degrades into noisy over-weighting of frequent
  attributes.

## 2. Discretization and math library

**Decision**: Use `numpy` only. `NumericBinner` computes quantile or uniform bin edges
from the corpus once per catalogue version; values map to `[0, 1]` directly. Add
`numpy` as an explicit dependency in `pyproject.toml`.

**Rationale**: `numpy` already installs transitively but must be declared to satisfy
the "no accidental dependency" rule. `scikit-learn`'s `KBinsDiscretizer` is the only
reason the prototype needs sklearn; replicating binning with numpy quantiles is small,
removes a heavy dependency, and avoids Python 3.14 wheel risk. This keeps the
established-library preference satisfied (numpy is the maintained library for the
numerical work).

**Alternatives considered**:
- Keep `scikit-learn` — rejected: heavy, uncertain Python 3.14 wheels, only used for one
  transformer.
- Keep `pandas` — rejected: only used to hold a DataFrame; the repository already has a
  Django model layer.
- Pure Python — rejected: slower for the O(N) scoring pass and reimplements numeric
  primitives that numpy already provides.

## 3. Plan attribute normalization

**Decision**: `PlanFeatureMapper` reads `PublishedRecord.values` and maps aliases to the
canonical dimensions `price`, `cpu`, `ram`, `disk`, `traffic`, `country`, `os`, reusing
`normalize_resource_value` and `RESOURCE_ALIASES` from `apps/catalog/filters.py`.
Missing attributes become masked dimensions.

**Rationale**: The existing normalized-resource helpers already handle unit conversion
and alias resolution; duplicating them would violate DRY. The mask is the mechanism for
FR-016 ("do not penalize undeclared attributes").

**Alternatives considered**:
- Compare raw JSON keys per plan — rejected: alias and unit drift produces meaningless
  distances.
- Introduce a second normalization layer in the new app — rejected: duplicated logic;
  instead the mapper imports the validation helper through the catalog interface.

## 4. Profile persistence

**Decision**: PostgreSQL models (`InterestProfile`, `InterestSignal`) are the source of
truth; the fitted `PlanSpace` matrix and lookups are cached in Redis with a catalogue
version key.

**Rationale**: Profiles carry privacy and merge semantics and must survive process
restarts; a database row makes the merge transaction and audit trail straightforward.
Redis-only state would lose profiles on flush and complicate transactional merging.
Caching only the derived, read-mostly plan space keeps the O(N) ranking path fast
without violating the source-of-truth rule (constitution V).

**Alternatives considered**:
- Redis-only profiles — rejected: durability, merge atomicity, and audit requirements.
- Recompute the fitted space per request — rejected: unnecessary CPU on a hot path.
- Persist the fitted space in Postgres — rejected: it is derived data with an
  invalidation lifecycle better suited to cache expiry.

## 5. Anonymous identity transport

**Decision**: Next middleware issues an opaque, random, httpOnly `visitor_id` cookie on
the frontend origin and injects `x-visitor-id` into the current request. Server
components forward that value to Django as `X-Visitor-Id`. Browser signal requests carry
the httpOnly cookie automatically. Django never accepts a client-supplied identity for
the merge.

**Rationale**: Catalogue pages are server-rendered (`frontend/app/page.tsx`,
`search/page.tsx`, `companies/[domain]/page.tsx`), so `localStorage` cannot influence
the first render. A cookie is readable by middleware and forwarded by server components,
works with the same-origin `/api/*` proxy (`frontend/next.config.ts`), and can be
httpOnly so scripts cannot read or forge it. The random value is not personal data.

**Alternatives considered**:
- `localStorage` vector — rejected: unavailable during server rendering and forgeable.
- Client-side re-fetch after hydration — rejected: visible reorder and wasted
  impressions; the initial order would not be the real one.
- Browser-side merge request — rejected by the user: it fragments the signal
  distribution and races with sign-in.
- Device fingerprint — rejected: privacy, reliability, and consent problems.

## 6. Ranking before pagination

**Decision**: Override `list()` in `PublishedPlansViewSet` for the related sort: filter
the queryset, materialise all matching records, score and sort in Python, then paginate
the ordered list with the existing envelope paginator. Price sorts keep the current SQL
path.

**Rationale**: `EnvelopeListViewSet.list` paginates the queryset before serialization
(`apps/utils/views.py`), so page 2 would otherwise not be the "next best" plans.
Overriding in the catalog viewset only keeps the shared base untouched and avoids
affecting other endpoints.

**Alternatives considered**:
- Order and slice in SQL — rejected: distances are computed in the preference space and
  depend on masked dimensions, which is not expressible as a simple ORM ordering.
- Client-side sorting after fetch — rejected: the API contract is server-paginated, and
  moving all plans to the client is worse for payload size and SSR.
- A custom DRF paginator that ranks during `paginate_queryset` — rejected: couples the
  generic pagination utility to recommendation logic.

## 7. Cold-start order

**Decision**: The cold-start prior is the masked mean of the declared dimensions across
the corpus, producing a deterministic vector. Ties break by `(-published_at, id)`.

**Rationale**: Satisfies FR-012 and FR-020 (same order for every viewer with no
interest) and avoids random ordering that would make tests and user expectations
unstable.

**Alternatives considered**:
- Random order — rejected: violates FR-012.
- Newest-first as the prior — rejected: makes the cold-start order identical to the
  previous default, hiding the feature's effect and biasing the prior toward recency.

## 8. Signal weights and bounded influence

**Decision**: Weight signals with a per-kind measurement noise `r` (destination 0.3,
details 0.8, search impression 1.5), and apply an ageing/decay step so repeated
identical signals have diminishing effect. All values are constance/settings-backed.

**Rationale**: Directly encodes FR-005 (graded strength) and FR-007 (bounded cumulative
influence) while keeping the update formula from the prototype. Configurable per
constitution XIII.

**Alternatives considered**:
- Equal weights — rejected: violates FR-005.
- Unbounded counters — rejected: violates FR-007 and lets one attribute dominate.

## 9. Search-impression signal

**Decision**: When a search query returns a first page, emit one signal carrying the
plan ids of that page; the recorder applies a single combined update using the centroid
of those candidates. Only the first page of a submitted query emits; empty queries and
later pages do not.

**Rationale**: Satisfies FR-006 and the spec edge cases. A per-result update would
overwhelm clicks with twelve weak signals.

**Alternatives considered**:
- One signal per result — rejected: violates FR-006.
- Only clicked search results — rejected: too sparse to personalise quickly for a
  demo-scale catalogue.
- Client-side aggregation — rejected: distribution of influence must stay server-side
  for consistency with the merge rule.

## 10. Merge semantics

**Decision**: Run the hand-off inside the existing OTP verify transaction
(`accounts/services/v1/accounts.py`). Under row locks: if the account profile exists,
it wins and the device profile is tombstoned with a link to the account; otherwise the
device profile is copied to the account and tombstoned. Late signals for a tombstoned
device profile are redirected to the linked account.

**Rationale**: Satisfies FR-008/FR-009 and the "soundness of the data distribution"
requirement — the merge is atomic, server-side, and cannot split a viewer's history.
Tombstoning prevents an in-flight pre-login signal from recreating an orphan profile.

**Alternatives considered**:
- A client-triggered merge endpoint — rejected by the user.
- Hard-delete the device profile during merge — rejected: an in-flight signal would
  recreate it and corrupt the distribution.
- Merge lazily on the next recommendation read — rejected: non-deterministic timing and
  harder to test.

## 11. Sign-out and retention

**Decision**: Sign-out clears the device cookie and removes the device profile's
contents; the account profile is retained. Profiles expire after a configurable period
of inactivity (default about six months). `InterestSignal` rows follow the same retention
window.

**Rationale**: Satisfies FR-010, privacy expectations, and constitution IX without
touching price history.

**Alternatives considered**:
- Keep the device profile after sign-out — rejected in the spec review for privacy.
- Delete the account profile on sign-out — rejected: breaks continuity on the next
  sign-in.

## 12. Abuse resistance and throttling

**Decision**: Apply a DRF throttle to the signal endpoint (per identity and per source)
and ignore signals beyond the configured per-minute cap. Do not accept a client-chosen
identity.

**Rationale**: Satisfies FR-019 with the project's existing throttling library instead
of custom counters.

**Alternatives considered**:
- No throttle — rejected: violates FR-019.
- Signed per-signal tokens — rejected: unnecessary complexity for a demo-scale feature.

## 13. Pagination stability

**Decision**: Order by `(distance, -published_at, id)` and recompute on each page
request. Accept that a signal between page loads can reshuffle results; document it.

**Rationale**: Satisfies FR-012/FR-013 for the normal case (interest unchanged) and
keeps the implementation simple. A frozen ranking token was judged out of scope for
this iteration.

**Alternatives considered**:
- Frozen ranking snapshot per query — rejected for now: needs a token or cache of the
  ordered identity list; can be added later without changing the contract.
- Cursor pagination over the ranked list — rejected: the frontend pagination and
  envelope already use page numbers.

## 14. Cache invalidation on publish

**Decision**: Key the cached plan space by a catalogue version derived from the
published records (for example the latest publish timestamp plus a count), and rebuild
when the key changes. Publishing a plan naturally moves the version.

**Rationale**: Keeps the fitted space consistent without wiring a cross-app signal into
the catalog publish path, and respects interface-only module boundaries.

**Alternatives considered**:
- Explicit invalidation call from the catalog publish service — rejected: introduces a
  catalog → recommendations dependency in the write path; the version key is simpler.
- No cache — rejected: rebuilds quantile binning on every request.
