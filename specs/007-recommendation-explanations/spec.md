# Feature Specification: Recommendation Explanations

**Feature Branch**: `007-recommendation-explanations`

**Created**: 2026-11-09

**Status**: Draft

**Input**: User description: "For the closest candidate in each cluster of a viewer's interests, explain why this is the closest recommendation to their interest. For each interest state space (three according to the settings), find the closest plan to the viewer's interest in that space. Divide the vector features into two categories: lexical/textual features and technical specifications. Determine which three features are closest to the viewer's interest (all ten textual dimensions are evaluated together, and the technical specifications are evaluated separately). Because features are normalized to 0-1, revert them to approximate the actual value of the viewer's interest. If a textual feature is among the three closest, explain simply that the viewer is interested in this category of products. For the rest, give a small range around the number obtained from normalization and explain, for example, that they have searched more for this CPU range."

## Context

Feature 005 ranks plans by comparing a viewer's preference state with a plan space, and
feature 006 keeps several interest clusters per viewer plus ten title-derived semantic
dimensions. Ranking is currently silent: the catalogue shows an ordered list and the
"suggested for you" strip without telling the viewer why any plan was chosen. This feature
adds a short, human-readable reason to the closest plan of each interest the viewer holds.

It also changes where recommendation state lives: the recommendation space, the fitted
plan vectors, and the explanation results MUST be persisted in the database (the source of
truth) so they survive cache eviction and restarts. Redis is a cache in front of that
persisted state, never the only home for it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Each interest shows its closest plan with a reason (Priority: P1)

A viewer who has shown interest in one or more themes opens the catalogue or the
"suggested for you" strip. For each theme the viewer holds, the closest matching plan is
shown together with one short sentence explaining which of the viewer's demonstrated
preferences made that plan the best match.

**Why this priority**: This is the whole feature. Without an explanation the feature
delivers nothing.

**Independent Test**: Record interest signals for one theme, load the suggested list, and
confirm the closest plan carries a readable reason that names the preference it matches.

**Acceptance Scenarios**:

1. **Given** a viewer with recorded interest in one theme, **When** the suggested plans load, **Then** the closest plan in that theme carries exactly one explanation sentence.
2. **Given** a viewer with several distinct interest themes, **When** the suggested plans load, **Then** each theme contributes its own closest plan and each carries its own explanation.
3. **Given** a viewer with no recorded interest, **When** the suggested plans load, **Then** no explanation is shown and the cold-start order is unchanged.

---

### User Story 2 - The reason names the features the viewer actually matched (Priority: P1)

The explanation is derived from the features closest to the viewer's stated interest. When
the closest match is driven by title-level (textual) similarity, the sentence says the
viewer is interested in that category of products. When it is driven by a technical
specification, the sentence names the specification and the approximate value range the
viewer has been leaning toward, expressed in real units rather than normalized scores.

**Why this priority**: A reason that names the real preference is what makes the feature
trustworthy instead of decorative.

**Independent Test**: For a viewer whose closest features are technical, confirm the
sentence names the technical attributes with real-unit ranges. For a viewer whose closest
features are textual, confirm the sentence describes a product category without exposing
raw numbers.

**Acceptance Scenarios**:

1. **Given** a viewer whose closest features include a textual (title-category) match, **When** an explanation is produced, **Then** it states interest in that category of products and does not expose normalized scores.
2. **Given** a viewer whose closest technical features include CPU, **When** an explanation is produced, **Then** it names CPU and quotes a small range in the real unit (for example, a range of CPU cores) rather than a 0-1 value.
3. **Given** several technical features are close, **When** an explanation is produced, **Then** at most three features are named.
4. **Given** the same viewer and the same recorded signals, **When** the explanation is produced again, **Then** the wording and the ranges are identical.

---

### User Story 3 - Explanations survive cluster and space changes (Priority: P2)

A viewer's interest clusters are bounded and can be replaced, and the recommendation space
can be refreshed. Explanations must keep working: every existing interest yields at most
one explanation, the number of explanations never exceeds the configured maximum, and a
missing or outdated preference never produces a broken or misleading reason.

**Why this priority**: Prevents the feature from surfacing stale, duplicated, or broken reasons after the underlying state changes.

**Independent Test**: Drive the profile past the cluster maximum, refresh the space, and confirm explanations remain one-per-interest and never exceed the cap.

**Acceptance Scenarios**:

1. **Given** a viewer with more distinct themes than the cluster cap, **When** explanations are produced, **Then** there is at most one explanation per retained cluster and never more than the configured maximum.
2. **Given** a profile whose stored preferences no longer match the active space, **When** the catalogue loads, **Then** the request succeeds and either a valid explanation or no explanation is returned.
3. **Given** a plan missing a named technical attribute, **When** an explanation would name that attribute, **Then** that attribute is omitted from the sentence rather than shown as zero or empty.

### Edge Cases

- Plan has no title or an empty title: textual features contribute nothing, so the reason is built from technical features only.
- Plan is missing every technical attribute used by the reason: no explanation is produced for that plan.
- Two clusters resolve to the same closest plan: show that plan once, with the reason from the interest that is closest to it.
- A cluster's stored preference is the cold-start prior (no real signal): treat as "no explanation".
- Selected feature reverts to a value outside the catalogue's observed range: clamp to the catalogue range before building the sentence.
- Reverting a normalized value lands on a categorical feature (for example country or OS): describe it by category name, not by a numeric range.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: For each interest cluster the viewer holds, the system MUST identify the single closest plan in the recommendation space.
- **FR-002**: The number of interest spaces considered MUST equal the number of active interest clusters and MUST NOT exceed the configured maximum.
- **FR-003**: The system MUST partition the plan-space dimensions into exactly two feature categories: textual/lexical features (the title-derived semantic dimensions) and technical specification features.
- **FR-004**: All textual dimensions MUST be evaluated together as a single textual feature group, and technical dimensions MUST be evaluated separately as a technical feature group.
- **FR-005**: The system MUST select the three feature groups/dimensions nearest to the viewer's stored preference for the given cluster, ranked by closeness.
- **FR-006**: The number of selected features and the number of interest spaces MUST be configurable and MUST NOT be hard-coded.
- **FR-007**: When a textual feature is among the closest, the explanation MUST state that the viewer is interested in that category of products, without exposing normalized scores.
- **FR-008**: For each selected technical feature, the explanation MUST quote a small range in the feature's real unit, derived by reverting the normalized value to the catalogue's actual value scale.
- **FR-009**: The system MUST NOT show more than three named features in one explanation.
- **FR-010**: The system MUST produce exactly one explanation sentence per retained interest cluster, and at most one explanation per plan.
- **FR-011**: A viewer with no recorded interest (cold-start prior) MUST receive no explanation, and the underlying ranking order MUST be unchanged.
- **FR-012**: Explanation text MUST be provided in the project's user-facing language(s) and MUST NOT expose internal identifiers, scores, versions, or dimension indexes.
- **FR-013**: The same viewer, signals, and space MUST always yield the same explanation text and the same ranges.
- **FR-014**: Missing plan attributes MUST be omitted from an explanation rather than rendered as zero or empty.
- **FR-015**: A profile whose dimensions or version do not match the active space MUST NOT produce a broken explanation; the request MUST still succeed.
- **FR-016**: The feature MUST NOT change the existing catalogue ordering, sort options, pagination, or signal capture behaviour.
- **FR-017**: Explanations MUST be available to the surface(s) that display suggested/related plans without adding a new user-facing action.
- **FR-018**: The range width used when quoting a technical feature MUST be configurable and MUST NOT be hard-coded.
- **FR-019**: The recommendation space (fitted vectors, version, and value scales) MUST be persisted in the database, and Redis MUST be used only as a cache in front of it, never as the sole store.
- **FR-020**: The generated explanation result for a viewer MUST be persisted in the database so it survives cache eviction and restarts and can be re-read without recomputation.
- **FR-021**: When the cache is empty or evicted, the system MUST serve the space and explanations from the database without recomputing from scratch, and when the database has no valid space it MUST rebuild and persist one.
- **FR-022**: The persisted space and explanations MUST carry the space version so a stale version is detected and rebuilt rather than served.

### Key Entities

- **Feature category**: One of the two groups every plan-space dimension belongs to — textual/lexical or technical specification.
- **Interest space (cluster)**: One stored preference position, one uncertainty vector, and the plan closest to it.
- **Closest-plan explanation**: The single sentence attached to a cluster's closest plan, naming up to three matched features in real-world terms.
- **Value conversion**: The reversal of a normalized dimension value back into the catalogue's real unit (for example CPU cores, GB of RAM, monthly price).
- **Persisted recommendation space**: The database record holding the fitted plan vectors, dimension names, value scales, and version — the cached entry is derived from it.
- **Persisted explanation result**: The database record holding a viewer's computed explanations keyed by space version, so repeated reads do not recompute.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a viewer with one interest, 100% of suggested-plan loads show the closest plan with exactly one explanation.
- **SC-002**: For a viewer with several interests up to the configured maximum, each retained interest contributes exactly one closest plan and no load shows more explanations than the configured maximum.
- **SC-003**: 100% of explanations are expressed in real units or category names, with 0 occurrences of raw normalized values, internal ids, or dimension indexes.
- **SC-004**: A viewer with no recorded interest sees 0 explanations in 100% of loads, and the cold-start order is identical to the order before this feature.
- **SC-005**: Repeating the same load with unchanged signals produces byte-identical explanation text in 100% of observed cases.
- **SC-006**: 100% of catalogue and suggested-plan requests succeed while explanations are produced, including for outdated profiles and after a space refresh.
- **SC-007**: At least 90% of test viewers can correctly restate why a plan was recommended after reading its explanation.
- **SC-008**: After a restart with an empty cache, 100% of suggested-plan loads still return the persisted space and explanations without a cold recalculation from raw plans.
- **SC-009**: 100% of served space and explanation data matches the active space version; a version mismatch is rebuilt, never served.

## Assumptions

- "Interest state spaces" refers to the viewer's interest clusters from feature 006; the count mirrors the active clusters and is bounded by the configured maximum cluster count.
- The three closest features are chosen from the two feature categories, with the ten textual dimensions counted as one textual feature and technical dimensions counted individually.
- Textual/phrase features are the ten title-derived semantic dimensions; technical features are the explicit attributes (price, CPU, RAM, disk, traffic, and categorical attributes such as country and OS).
- "Reverting normalization" reuses the plan space's existing value scale so a reverted value approximates the real value a matching plan would declare.
- The existing ranking and interest-profile data are reused; no new user-facing action is introduced.
- Explanations are produced only where suggested/related plans are already shown (for example the "suggested for you" strip); the main catalogue list ordering is unchanged.
- A default of three named features and a small configurable range width are used when the description leaves the numbers unspecified.
- "Persisted" means stored as a database row (PostgreSQL, the source of truth); Redis remains a cache that can be evicted at any time without losing the space or explanations.
- The persisted space and explanation records follow the project's model conventions (shared timestamped base model, soft delete, audit logging). No data migration is needed for existing crawler data because the space is recomputed and re-persisted on refresh.

## Dependencies

- Feature 005 recommendation space, ranking, and signals.
- Feature 006 interest clusters and ten semantic dimensions.
- The existing plan space, its numeric binners, and its categorical vocabularies.
- Existing i18n catalogs for user-facing copy.
- PostgreSQL (persistence of the space and explanation results) and Redis (cache only).
