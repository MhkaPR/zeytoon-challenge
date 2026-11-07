# Feature Specification: Periodic PCA Space Expansion

**Feature Branch**: `006-pca-space-expansion`

**Created**: 2026-11-07

**Status**: Draft

**Input**: User description: "Read `pca.py`. I want these algorithms calculated at periodic times, and add 10 dimensions to the recommendation space in Redis so the Kalman filter can be calculated more precisely. Read `specs/005-related-plans-sort` for correct context."

## Context

Feature `005-related-plans-sort` ranks plans for each viewer by comparing the viewer's
preference position against a fitted plan space. That space currently contains only
explicit plan attributes (price, CPU, memory, disk, traffic, location, operating system).
The prototype `pca.py` shows a second, complementary view of a plan: a compact set of
semantic components derived from the plan's title through character n-gram hashing and
principal component analysis.

This feature makes that semantic view part of the live recommendation space. The
semantic components are recalculated on a schedule and added to the cached plan space,
so each viewer's Kalman-style preference state can estimate intent across both explicit
attributes and title semantics.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Semantic space refreshed on a schedule (Priority: P1)

An operator relies on the recommendation space staying current as the catalogue changes.
On a configured schedule, the platform recalculates the semantic components from the
current published plan titles and publishes an updated space, without any manual step
and without interrupting catalogue requests.

**Why this priority**: Without the periodic recalculation there is no new information for
the recommender, so this is the foundation of the feature.

**Independent Test**: Publish or edit a plan title, trigger the scheduled recalculation,
and confirm the cached space reports a new version containing the updated semantic
components while catalogue requests continue to succeed during the swap.

**Acceptance Scenarios**:

1. **Given** a schedule is configured, **When** the scheduled time arrives, **Then** the semantic components are recalculated from the current published plans and the cached space is replaced as one atomic update.
2. **Given** a catalogue request during a recalculation, **When** the request reads the space, **Then** it receives either the previous complete space or the new complete space, never a partially updated one.
3. **Given** the recalculation completes, **When** an operator inspects the space version, **Then** the version reflects the new plan corpus and the recalculation time.
4. **Given** no plan titles changed since the previous run, **When** the recalculation runs, **Then** the resulting semantic components and cold-start order are unchanged.

---

### User Story 2 - Recommendations use ten additional semantic dimensions (Priority: P1)

A visitor browses plans whose titles signal a category (for example gaming, storage,
email, WordPress, or GPU workloads). The viewer's preference state now tracks those ten
semantic dimensions in addition to the explicit attributes, so the related order reflects
both what the plan offers and what its title communicates.

**Why this priority**: This is the user-visible payoff of the feature; without it the
recalculation has no effect on ordering.

**Independent Test**: Record interest in plans sharing one title theme, reload the
catalogue, and confirm plans with that theme rank higher than they did before the semantic
dimensions existed, while explicit-attribute ordering still behaves as in feature 005.

**Acceptance Scenarios**:

1. **Given** the expanded space, **When** a viewer's preference state is created, **Then** it contains a value and an uncertainty for every explicit dimension and every one of the ten semantic dimensions.
2. **Given** a viewer records interest in plans with a shared title theme, **When** the catalogue loads next, **Then** plans with that theme rank higher than they did before the signal.
3. **Given** a plan whose title carries little semantic signal, **When** it is ranked, **Then** its semantic dimensions are treated as neutral rather than as a penalty.
4. **Given** a viewer with no recorded interest, **When** the catalogue loads, **Then** the cold-start order remains deterministic and identical for all such viewers.

---

### User Story 3 - Existing viewers continue without corruption (Priority: P2)

A viewer who already has a preference history returns after the space has been expanded
from the previous dimension set to the new one. Their stored state is reconciled with the
new space so that ranking never fails and no visitor silently inherits another visitor's
preferences.

**Why this priority**: The change alters the shape of stored preference data; without a
safe reconciliation the feature would break existing viewers.

**Independent Test**: Seed a profile produced against the previous space, load the
catalogue, and confirm the request succeeds, the profile is reconciled to the new shape,
and the resulting order is deterministic.

**Acceptance Scenarios**:

1. **Given** a stored profile whose dimensions do not match the active space, **When** it is read, **Then** it is reconciled to the active space without an error.
2. **Given** a reconciled profile, **When** the same catalogue is loaded twice with no new signals, **Then** both loads return the same order.
3. **Given** a space replacement, **When** profiles are reconciled, **Then** no profile is attributed to a different viewer and no preference is copied between viewers.
4. **Given** the previous space remains cached, **When** reconciliation runs, **Then** the previous space is still usable until the new one is complete.

---

### User Story 4 - Failed or stale recalculation is safe (Priority: P2)

An operator needs confidence that a failed recalculation cannot degrade the catalogue.
If the scheduled calculation fails or produces an invalid result, the last known-good
space continues to serve requests and the failure is visible to operators.

**Why this priority**: Recommendations are a live path; a bad refresh must never take the
catalogue down or produce arbitrary ordering.

**Independent Test**: Force the recalculation to fail and confirm catalogue requests keep
using the previous space, the failure is recorded, and the next scheduled run can recover.

**Acceptance Scenarios**:

1. **Given** a recalculation failure, **When** catalogue requests arrive, **Then** they continue to use the last known-good space and ordering remains deterministic.
2. **Given** an invalid or empty result, **When** the recalculation finishes, **Then** the previous space is retained and the run is reported as failed.
3. **Given** a later successful recalculation, **When** it completes, **Then** the space is replaced and the failure state clears.
4. **Given** a recalculation that takes longer than the schedule interval, **When** the next run is due, **Then** overlapping runs do not corrupt the cached space.

---

### Edge Cases

- The catalogue is empty or has only one published plan: the semantic components are neutral and ordering remains valid.
- A plan has an empty, duplicated, or non-Persian title: it still receives a position and is never excluded from ranking.
- Two plans share an identical title: both receive the same semantic components and remain distinguishable by their explicit attributes and identifiers.
- The number of published plans is smaller than the number of semantic dimensions: the recalculation still produces the full configured dimension count using neutral values where information is insufficient.
- A plan is published, unpublished, or retired between scheduled runs: it is reflected on the next run; until then the previous space remains valid.
- The cache is cleared or unavailable: the space is rebuilt from the current published plans without changing the cold-start order.
- A viewer's preference state was created against an older space version: it is reconciled on read rather than rejected.
- The scheduled recalculation runs while a viewer is actively browsing: the viewer's next request uses a consistent space and does not mix dimensions from two versions.
- The configured semantic dimension count is changed by an operator: the space version changes and profiles are reconciled accordingly.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST recalculate the semantic plan components on a configurable periodic schedule without manual intervention.
- **FR-002**: The recalculation MUST derive the semantic components from the titles of currently published plans using the same family of text-to-vector and dimensionality-reduction steps demonstrated in `pca.py`.
- **FR-003**: The expanded recommendation space MUST contain exactly ten additional semantic dimensions on top of the existing explicit-attribute dimensions.
- **FR-004**: The number of semantic dimensions MUST be configurable, with ten as the default.
- **FR-005**: The recalculation schedule MUST be configurable, with a documented default interval.
- **FR-006**: The cached recommendation space MUST be replaced atomically so readers never observe a partially updated space.
- **FR-007**: Each cached space MUST carry a version that changes when the plan corpus or the semantic configuration changes.
- **FR-008**: A viewer's preference state MUST cover every dimension of the active space, including the ten semantic dimensions.
- **FR-009**: A stored preference state whose dimensions do not match the active space MUST be reconciled to the active space without failing the request.
- **FR-010**: Reconciliation of an outdated preference state MUST preserve viewer isolation: no preference may be copied between viewers or identities.
- **FR-011**: The cold-start related order MUST remain deterministic and identical for all viewers with no recorded interest after the space is expanded.
- **FR-012**: Plans that carry little or no semantic title signal MUST be treated as neutral on the semantic dimensions rather than penalized.
- **FR-013**: A failed or invalid recalculation MUST NOT replace the last known-good space.
- **FR-014**: Recalculation failures MUST be observable to operators through the project's existing logging and monitoring conventions.
- **FR-015**: Overlapping scheduled recalculation runs MUST NOT corrupt the cached space.
- **FR-016**: The existing explicit-attribute ranking behaviour and all feature 005 requirements MUST continue to hold after the expansion.
- **FR-017**: The recalculation MUST NOT require changes to the public catalogue or signal-submission contracts.
- **FR-018**: The semantic components MUST be reproducible for the same plan corpus and configuration.
- **FR-019**: The recalculation MUST tolerate a catalogue containing fewer plans than semantic dimensions.
- **FR-020**: The system MUST NOT block catalogue requests while the recalculation is running.

### Key Entities *(include if feature involves data)*

- **Semantic plan profile**: The ten-component representation of one published plan derived from its title, stored as part of the cached recommendation space.
- **Expanded plan space**: The cached recommendation space that combines the existing explicit-attribute dimensions with the ten semantic dimensions, carries a version, and is shared by all viewers.
- **Preference state**: A viewer's per-dimension position and uncertainty across the expanded space, reconciled when the space version changes.
- **Recalculation run**: One scheduled execution that reads the current published plan corpus, computes semantic components, validates the result, and publishes a new space version.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of scheduled recalculation runs complete without manual intervention, within the configured interval.
- **SC-002**: Catalogue requests never observe a partially updated space; 100% of requests return an order from one complete space version.
- **SC-003**: After a recalculation, 100% of newly created preference states cover all explicit and semantic dimensions.
- **SC-004**: 100% of requests from viewers with outdated preference states succeed after reconciliation.
- **SC-005**: Two viewers with no recorded interest see the same catalogue order in 100% of observed loads after the expansion.
- **SC-006**: After a viewer records interest in plans sharing one title theme, plans with that theme rank higher on the next catalogue load in every observed case.
- **SC-007**: A failed recalculation leaves the previous order unchanged in 100% of observed requests.
- **SC-008**: The expanded space adds exactly ten semantic dimensions by default, verified by inspecting the cached space metadata.
- **SC-009**: Recalculation of an unchanged plan corpus produces the same semantic components and cold-start order in 100% of repeated runs.

## Assumptions

- The default recalculation interval is daily; operators can change it without a deployment.
- Semantic components are derived from plan titles only, matching `pca.py`; other text fields are out of scope for this iteration.
- The prototype's character n-gram hashing and principal component analysis are the intended algorithm family; the exact implementation is decided during planning.
- Ten semantic dimensions are added, not substituted; the existing explicit-attribute dimensions remain unchanged.
- The cached space continues to live in the shared cache used by feature 005, keyed by space version.
- Outdated preference states are reconciled by resetting the affected dimensions to the cold-start position and full uncertainty; historical signals are retained for diagnostics.
- Recalculation failures are reported through the project's existing logging and monitoring conventions; no new alerting channel is introduced.
- The feature is validated manually by the team for this iteration; no automated success-measurement pipeline is in scope.

## Dependencies

- The recommendation space, preference state, ranking, and signal behaviour delivered by `specs/005-related-plans-sort`.
- The published-plan catalogue and its plan titles.
- The shared cache used for the fitted plan space.
- The project's scheduling mechanism for periodic background work.
- The project's logging and monitoring conventions.
