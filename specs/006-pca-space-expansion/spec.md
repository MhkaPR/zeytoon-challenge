# Feature Specification: Periodic PCA Space Expansion

**Feature Branch**: `006-pca-space-expansion`

**Created**: 2026-11-07

**Status**: Draft

**Input**: User description: "Read `pca.py`. Calculate these algorithms periodically and add 10 dimensions to the recommendation space in Redis so the Kalman filter is more precise. Read `specs/005-related-plans-sort` for context."

## Context

Feature 005 ranks plans by comparing a viewer's preference state with a plan space built
from explicit attributes. `pca.py` adds a second view: a compact semantic representation
of each plan derived from its title. This feature adds ten such semantic dimensions to
the existing space and refreshes them on a schedule.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ten semantic dimensions are added and refreshed (Priority: P1)

On a schedule, the platform recalculates semantic components from current plan titles
and adds ten dimensions to the recommendation space. Viewers' preference states then
track both explicit attributes and title meaning, so recommendations improve.

**Why this priority**: This is the whole feature.

**Independent Test**: Run the refresh, inspect the cached space, and confirm it has ten
semantic dimensions and a new version. Record interest in plans sharing a title theme and
confirm they rank higher.

**Acceptance Scenarios**:

1. **Given** published plans, **When** the refresh runs, **Then** the cached space contains ten semantic dimensions and a version derived from the current plans.
2. **Given** the expanded space, **When** a viewer's state is created, **Then** it has a value and uncertainty for every dimension.
3. **Given** interest in plans sharing a title theme, **When** the catalogue loads, **Then** plans with that theme rank higher.
4. **Given** no recorded interest, **When** the catalogue loads, **Then** the cold-start order is deterministic.

---

### User Story 2 - Existing viewers and failed refreshes stay safe (Priority: P2)

An existing viewer's stored state may not match the new dimension count, and a refresh
may fail. In both cases the catalogue must keep working.

**Why this priority**: Prevents the change from breaking live requests.

**Independent Test**: Load a profile with the old dimension count and confirm the request
succeeds. Force a refresh failure and confirm the previous space is still served.

**Acceptance Scenarios**:

1. **Given** a profile with an outdated dimension count or space version, **When** it is read, **Then** it is rebuilt from the cold-start prior without error.
2. **Given** a failed refresh, **When** the catalogue loads, **Then** the previous space is used and ordering is unchanged.
3. **Given** no public API change, **When** feature 005 tests run, **Then** they still pass.

---

### User Story 3 - Multiple interests are kept at the same time (Priority: P1)

A viewer searches and clicks plans from several themes, for example python, node, and
email. The recommendation keeps all three interests instead of collapsing into whichever
theme was clicked most recently.

**Why this priority**: This is the behaviour the viewer expects; a single averaged
interest makes the recommendation swing to one theme.

**Independent Test**: Record signals for three distinct themes and confirm the profile
holds one interest cluster per theme and the top catalogue results include plans from all
three themes.

**Acceptance Scenarios**:

1. **Given** a viewer records interest in three distinct themes, **When** the catalogue loads, **Then** the profile holds up to the configured maximum number of interest clusters and plans from each theme rank near the top.
2. **Given** a new signal close to an existing interest, **When** it is recorded, **Then** it updates that interest instead of creating a duplicate cluster.
3. **Given** a new signal far from every existing interest, **When** it is recorded, **Then** a new cluster is created until the configured maximum is reached.
4. **Given** the maximum number of clusters is reached, **When** another distinct theme arrives, **Then** the least confident cluster is replaced and the profile remains bounded.
5. **Given** a profile stored as one flat vector before this change, **When** it is read, **Then** it is treated as a single cluster and continues to work.

### Edge Cases

- Empty catalogue or fewer plans than dimensions: neutral semantic values, no error.
- Empty or missing title: neutral semantic values, not a penalty.
- Duplicate titles: identical semantic values, still distinguished by other attributes.
- Cache cleared: the space is rebuilt on the next read.
- More distinct themes than the cluster cap: the least confident cluster is replaced.
- A flat legacy profile: treated as one cluster without a migration.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST recalculate semantic components on a configurable schedule.
- **FR-002**: Semantic components MUST be derived from published plan titles using the `pca.py` algorithm family (character n-gram hashing + PCA).
- **FR-003**: The expanded space MUST add exactly ten semantic dimensions by default, and the count MUST be configurable.
- **FR-004**: A viewer's preference state MUST cover every dimension of the active space.
- **FR-005**: A profile whose dimensions or version do not match the active space MUST be rebuilt from the cold-start prior without failing.
- **FR-006**: The cold-start order MUST remain deterministic and identical for all viewers with no interest.
- **FR-007**: Empty or missing titles MUST be treated as neutral on semantic dimensions.
- **FR-008**: A failed refresh MUST NOT replace the last working space.
- **FR-009**: The feature MUST NOT change the public catalogue or signal API.
- **FR-010**: Existing feature 005 ranking, sorting, pagination, and signal behaviour MUST keep working.
- **FR-011**: A viewer profile MUST store up to a configurable maximum number of interest clusters (default three).
- **FR-012**: A signal MUST update the nearest existing interest cluster when it is within the configured distance threshold.
- **FR-013**: A signal farther than the threshold from every cluster MUST create a new cluster until the maximum is reached.
- **FR-014**: When the maximum is reached, the least confident cluster MUST be replaced so the profile stays bounded.
- **FR-015**: Ranking MUST use the minimum distance across all of a viewer's interest clusters.
- **FR-016**: A legacy profile stored as one flat position vector MUST be read as a single cluster without a data migration.

### Key Entities

- **Semantic plan profile**: Ten title-derived values per published plan.
- **Expanded plan space**: The cached space with explicit attributes plus ten semantic dimensions and a version.
- **Preference state**: A viewer's position and uncertainty across the expanded space.
- **Interest cluster**: One position and uncertainty vector representing one theme the viewer is interested in; a profile holds up to the configured maximum.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The cached space contains exactly ten semantic dimensions by default.
- **SC-002**: 100% of catalogue requests succeed before, during, and after a refresh.
- **SC-003**: Requests from viewers with outdated profiles succeed in 100% of cases.
- **SC-004**: Two viewers with no interest see the same order in 100% of observed loads.
- **SC-005**: A failed refresh leaves the previous order unchanged in 100% of observed requests.
- **SC-006**: After signals for three distinct themes, the top catalogue results include plans from all three themes in 100% of observed loads.
- **SC-007**: A profile never holds more than the configured maximum number of interest clusters.

## Assumptions

- The default refresh interval is daily; the operator changes it in the scheduler.
- Only plan titles are used for semantic components.
- Ten dimensions are added, not substituted.
- The existing cache is reused; no new datastore is introduced.
- Outdated profiles are reset to the cold-start prior; no data migration is needed.
- The default maximum number of interest clusters is three; operators can change it.
- A flat legacy profile is treated as one cluster.

## Dependencies

- Feature 005 recommendation space, ranking, and signals.
- Published plan titles.
- The existing cache and scheduling mechanism.
