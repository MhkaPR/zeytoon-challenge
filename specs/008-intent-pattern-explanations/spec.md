# Feature Specification: Intent-Pattern Recommendation Explanations

**Feature Branch**: `008-intent-pattern-explanations`

**Created**: 2026-11-10

**Status**: Draft

**Input**: User description: "Replace feature-based recommendation explanations with intent-pattern explanations. For each interest cluster, build the top-K nearest plans and score pre-declared intent patterns against that candidate set using Lift, Fisher Exact, and MCC gates. Determine one intent per cluster, then display only the most relevant intent in the UI by counting how often each intent appears across clusters. Remove the separate explanation endpoint and persisted explanation model."

## Context

Feature 005 ranks plans per interest cluster and returns the top-K nearest plans. Feature
006 adds semantic dimensions and keeps several interest clusters per viewer. The current
explanation layer describes which normalized feature drove the ranking, for example a RAM
band. That approach has three product problems:

1. It describes attributes rather than intent. A viewer who explores a cheap plan and then
   a premium plan is comparing trade-offs, not expressing two contradictory interests.
2. Its feature-overlap score favors narrow, low-prevalence bands that happen to fall inside
   the candidate set even when they carry no meaningful intent signal.
3. It is computed by a separate endpoint and can reference plans or space versions that
   differ from the suggested-plans response.

This feature replaces attribute descriptions with intent-pattern explanations. Each
cluster's candidate set is compared against a small, pre-declared set of intent patterns.
Only patterns that pass sample-size, statistical-significance, effect-size, and
signal-corroboration checks may be reported. When no real pattern qualifies, the viewer
receives a neutral "exploring" message.

Intent detection still happens per cluster, so the system never averages cluster
positions. The user interface, however, shows only one primary intent: the intent that
appears most often across the viewer's clusters. This keeps the message short and avoids
showing several competing explanations at once.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The viewer sees an intent explanation, not an attribute range (Priority: P1)

A viewer with one or more interest clusters sees one short sentence that describes the
most relevant intent behind the recommended plans, such as seeking value for money or high
resources, instead of a numeric attribute range. The system still determines an intent for
each cluster internally, but the interface presents a single primary intent.

**Why this priority**: This is the core product change. Without it the feature delivers no
user-visible improvement.

**Independent Test**: Seed a viewer whose interactions favor value-for-money plans, load
the suggested plans, and confirm the displayed explanation names the value intent and
contains no attribute range.

**Acceptance Scenarios**:

1. **Given** a viewer with one or more interest clusters whose candidate plans match real intent patterns, **When** suggested plans load, **Then** the interface displays exactly one primary intent message.
2. **Given** any reported explanation, **When** its message is inspected, **Then** it contains no numeric range derived from a feature bin center.
3. **Given** a value-driven viewer, **When** the explanation is produced, **Then** the reported intent is `value`, not a RAM or price attribute description.

---

### User Story 2 - The primary intent reflects the most frequent cluster intent (Priority: P1)

A viewer with several distinct interests may have different intents detected in different
clusters. The interface shows the intent that occurs in the largest number of clusters, so
the viewer gets one coherent message instead of several competing or contradictory ones.

**Why this priority**: Multi-cluster coherence is the main reason the attribute-based
approach fails. Per-cluster detection must remain correct, while the visible message must
stay singular and understandable.

**Independent Test**: Seed a viewer with three clusters whose detected intents are `value`,
`value`, and `cheap`, load the suggested plans, and confirm the interface shows `value`
with an occurrence count of two.

**Acceptance Scenarios**:

1. **Given** three clusters whose detected intents are `value`, `value`, and `cheap`, **When** the suggested plans load, **Then** the primary intent is `value` and its occurrence count is two.
2. **Given** two or more intents with the same occurrence count, **When** the primary intent is chosen, **Then** the tie is resolved deterministically by confidence and the fixed intent order.
3. **Given** multiple clusters, **When** intents are detected, **Then** each cluster is evaluated independently and cluster positions are never averaged together.
4. **Given** a cheap cluster and a premium cluster, **When** the primary intent is shown, **Then** the message is not an attribute range and does not combine contradictory attribute bands.

---

### User Story 3 - An honest fallback is used when no intent qualifies (Priority: P1)

A viewer with random clicks, a cold-start profile, or otherwise weak evidence receives a
neutral "exploring" message instead of a fabricated intent or an attribute description.

**Why this priority**: Trust depends on not overstating weak evidence. The fallback is the
safety valve for every case where the statistical and corroboration checks fail.

**Independent Test**: Seed a viewer with random or insufficient clicks, load the suggested
plans, and confirm the cluster reports `exploring` with the fixed message and no confidence
values.

**Acceptance Scenarios**:

1. **Given** no cluster has a real intent pattern that passes all gates and corroboration, **When** the primary intent is produced, **Then** the intent is `exploring`, the direction is absent, the confidence is absent, and the fixed exploring message is returned.
2. **Given** at least one cluster has a real intent pattern that passes all gates and corroboration, **When** the primary intent is produced, **Then** the response reports that real pattern and never `exploring`.
3. **Given** a cold-start profile, **When** suggested plans load, **Then** the primary intent is `exploring` and the plan ordering is unchanged from the existing cold-start behavior.

---

### User Story 4 - One source of truth for suggested plans and explanations (Priority: P2)

The explanation shown for a cluster is computed in the same request that produces the
suggested plans, so the message can never describe a different plan set or space version
than the one the viewer sees.

**Why this priority**: Drift between the separate explanation endpoint and the suggested
plans response is one of the defects being removed.

**Independent Test**: Load the suggested-plans response and confirm every explanation
belongs to a cluster represented in that same response; confirm the separate explanation
endpoint and its persisted explanation records are gone.

**Acceptance Scenarios**:

1. **Given** a suggested-plans request, **When** the response is produced, **Then** each interest cluster in the response carries its explanation.
2. **Given** the old separate explanation endpoint, **When** the feature is complete, **Then** the endpoint no longer exists.
3. **Given** the old persisted explanation records, **When** the feature is complete, **Then** no persisted explanation model remains and no new persisted explanation state is introduced.

---

### User Story 5 - Explanations are deterministic and configurable (Priority: P2)

The same viewer profile and the same catalog version always produce the same explanation.
Operators can tune the candidate size and statistical thresholds without a code change.

**Why this priority**: Determinism makes the feature testable and trustworthy; runtime
configuration keeps statistical policy adjustable in production.

**Independent Test**: Produce explanations twice for the same profile and catalog version
and compare the responses byte for byte. Change a configured threshold and confirm the
outcome follows the new value.

**Acceptance Scenarios**:

1. **Given** an unchanged profile and catalog version, **When** explanations are produced twice, **Then** the responses are byte-identical.
2. **Given** an operator changes a configured explanation threshold, **When** the next explanation is produced, **Then** the new threshold is applied without a code deployment.
3. **Given** a pattern registry, **When** a new intent pattern is added, **Then** the scoring and gate logic does not need to change.

---

### Edge Cases

- A pattern with fewer than the minimum required catalog members is never reported, even if every one of its members appears in the candidate set.
- A pattern with a statistically significant but weak association is never reported.
- A pattern with a strong association but no directional signal is never reported.
- A pattern that passes every numeric gate but contradicts the viewer's click history is rejected.
- A real pattern that qualifies must win over `exploring`; `exploring` is never scored as a competitor.
- Clusters whose detected intent is `exploring` do not outvote clusters that have a real intent; `exploring` is shown only when every cluster is exploring.
- When two intents have the same cluster count, the tie is resolved by summed confidence and then by a fixed intent order so the result is deterministic.
- A cluster with an empty or unusably small candidate set falls back to `exploring`.
- A catalog smaller than the configured candidate size still produces a deterministic explanation or the `exploring` fallback.
- A viewer with fewer than the configured minimum number of outbound clicks fails corroboration for every real pattern and receives `exploring`.
- A stale profile or space version does not crash the request; the existing rebuild behavior is preserved.
- A pattern whose member set exactly equals the candidate set or exactly excludes it must not divide by zero in scoring.

## Requirements *(mandatory)*

### Functional Requirements

**Intent pattern catalog**

- **FR-001**: The system MUST define exactly five intent patterns: `cheap`, `value`, `spec_heavy`, `premium`, and `exploring`.
- **FR-002**: The four real patterns MUST be evaluated as predicates over normalized plan features: `cheap` when price percentile is below 0.30; `value` when the gap between spec percentile and price percentile exceeds 0.15; `spec_heavy` when the mean of RAM, CPU, and disk percentiles exceeds 0.70; and `premium` when both price percentile and spec percentile exceed 0.70.
- **FR-003**: The `exploring` pattern MUST be a fallback only and MUST NOT be scored, ranked, or compared against the four real patterns.
- **FR-004**: The pattern registry MUST NOT contain a `text_specific` or keyword-based pattern in this iteration.
- **FR-005**: Adding a new intent pattern MUST require only registering its predicate and messages, not changing the scoring or gate logic.

**Candidate set and per-cluster evaluation**

- **FR-006**: For each interest cluster, the system MUST build the candidate set from the configured number of nearest catalog plans, using the same ranking basis as the suggested-plans response.
- **FR-007**: Each cluster MUST be evaluated independently; cluster positions MUST NOT be averaged or combined.
- **FR-008**: For each real pattern, the system MUST construct the 2x2 contingency table of pattern membership versus candidate-set membership using the full catalog as the population.

**Statistical and effect-size gates**

- **FR-009**: A real pattern MUST be rejected when its total catalog membership is below the configured minimum sample size.
- **FR-010**: A real pattern MUST be rejected when its two-sided Fisher Exact Test p-value exceeds the configured significance threshold.
- **FR-011**: A real pattern MUST be rejected when its Lift, defined as the candidate-set share of the pattern divided by the candidate-set share of the catalog, is below the configured minimum Lift.
- **FR-012**: A real pattern MUST be rejected when the absolute value of its Matthews Correlation Coefficient is below the configured minimum MCC.
- **FR-013**: The MCC sign MUST determine direction: a positive MCC reports a positive interest and a negative MCC reports an avoidance.
- **FR-014**: Among real patterns that pass every gate and corroboration check, the system MUST select the pattern with the highest score, where score is Lift multiplied by the absolute MCC.

**Signal corroboration**

- **FR-015**: A real pattern MUST be rejected unless the viewer has at least the configured minimum number of outbound clicks associated with that cluster.
- **FR-016**: For `cheap`, the mean price percentile of the corroborating clicks MUST be below 0.40.
- **FR-017**: For `spec_heavy`, the mean spec percentile of the corroborating clicks MUST be above 0.60.
- **FR-018**: For `value`, the mean gap between spec percentile and price percentile of the corroborating clicks MUST be above 0.10.
- **FR-019**: For `premium`, the mean price percentile of the corroborating clicks MUST be above 0.60.
- **FR-020**: A real pattern that passes every numeric gate but fails its corroboration condition MUST NOT be reported.

**Explanation output**

- **FR-021**: Each interest cluster in the suggested-plans response MUST carry exactly one explanation object containing intent, direction, message, and confidence.
- **FR-022**: A real-pattern explanation MUST report the pattern key as intent, the direction derived from MCC, a confidence object containing Lift, p-value, and MCC, and the Persian message for that pattern and direction.
- **FR-023**: The Persian messages for positive real patterns MUST be: `cheap` — «دنبال گزینه‌های اقتصادی با قیمت پایین هستی»; `value` — «دنبال بهترین نسبت امکانات به قیمت هستی»; `spec_heavy` — «دنبال منابع بالا (رم/CPU/دیسک) هستی»; `premium` — «دنبال گزینه‌های پرقدرت و حرفه‌ای هستی».
- **FR-024**: When no real pattern qualifies, the explanation MUST report intent `exploring`, no direction, no confidence, and the message «در حال کاوش گزینه‌های مختلف هستی».
- **FR-025**: No explanation message may contain a numeric range tied to a feature bin center. Naming a resource category as part of an intent sentence is permitted only without a range.
- **FR-026**: `exploring` MUST NOT be returned when at least one real pattern passes all gates and corroboration.

**Single source of truth and lifecycle**

- **FR-027**: Explanations MUST be computed inside the suggested-plans request rather than by a separate endpoint.
- **FR-028**: The separate explanation endpoint MUST be removed.
- **FR-029**: The persisted explanation model and any persisted explanation results MUST be removed.
- **FR-030**: The feature MUST NOT introduce a new persisted model or a database migration.
- **FR-031**: Explanation computation MUST be deterministic for the same profile and catalog version.
- **FR-032**: The candidate size, minimum pattern size, significance threshold, minimum Lift, minimum MCC, and minimum click count MUST be runtime-configurable with the defaults `20`, `30`, `0.05`, `2.0`, `0.20`, and `3` respectively.

**Primary intent for the interface**

- **FR-033**: The system MUST determine one intent per interest cluster before producing the interface explanation.
- **FR-034**: The system MUST count how many clusters produced each real intent and MUST select the intent with the highest count as the primary intent.
- **FR-035**: Clusters whose intent is `exploring` MUST NOT contribute to the count of a real intent; `exploring` MUST become the primary intent only when every cluster is `exploring`.
- **FR-036**: When two or more real intents share the highest count, the system MUST break the tie first by the highest summed confidence score of the clusters carrying that intent, where confidence score is Lift multiplied by absolute MCC, and then by the fixed order `cheap`, `value`, `spec_heavy`, `premium`.
- **FR-037**: The primary explanation MUST carry the intent, direction, message, and confidence of the highest-scoring cluster that produced the winning intent.
- **FR-038**: The primary explanation MUST include the number of clusters that produced the winning intent and the total number of clusters evaluated.
- **FR-039**: The suggested-plans response MUST include the primary explanation alongside the per-cluster explanations.
- **FR-040**: The interface MUST render only the primary intent message once, not one message per cluster.
- **FR-041**: Primary-intent selection MUST be deterministic for the same profile and catalog version.

### Key Entities

- **Intent pattern**: A named predicate over normalized plan features that selects a subset of the catalog, plus its user-facing message and its fallback status.
- **Candidate set**: The configured number of catalog plans nearest to one interest cluster; the set against which every real pattern is scored.
- **Contingency table**: The counts of pattern members inside and outside the candidate set, and candidate-set members inside and outside the pattern, used by all three statistical gates.
- **Intent explanation**: The per-cluster result containing the selected intent, direction, confidence values, and message.
- **Primary intent summary**: The single interface-facing result chosen by counting per-cluster intents, carrying the winning intent's message and confidence plus its occurrence count and the total cluster count.
- **Corroborating click**: A viewer interaction associated with a cluster and used to confirm that the statistically detected intent matches the viewer's actual behavior.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a seeded value-driven viewer, 100% of suggested-plan loads report `value` as the cluster explanation and 0% report an attribute range.
- **SC-002**: For a viewer with two distinct intents, 100% of loads show exactly one primary intent message and 0% show contradictory attribute ranges.
- **SC-003**: 0% of explanation messages contain a numeric range tied to a feature bin center.
- **SC-004**: 0% of reported patterns have fewer than the configured minimum catalog membership.
- **SC-005**: 0% of reported patterns have a p-value above the configured significance threshold, even when Lift exceeds 3.
- **SC-006**: 0% of reported patterns have Lift below the configured minimum.
- **SC-007**: 0% of reported patterns have absolute MCC below the configured minimum.
- **SC-008**: 0% of reported patterns contradict the viewer's corroborating click history.
- **SC-009**: 100% of cold-start or random-click viewers receive `exploring` with the fixed message and no confidence values.
- **SC-010**: 100% of cases with at least one qualifying real pattern report that pattern and never `exploring`.
- **SC-011**: Repeating the same profile and catalog version produces byte-identical explanations in 100% of observed cases.
- **SC-012**: 100% of feature-005 and feature-006 regression tests still pass.
- **SC-013**: The pattern registry contains exactly the five approved keys and 0 keyword-based patterns.
- **SC-014**: When one real intent appears in more clusters than any other, 100% of loads select that intent as the primary intent.
- **SC-015**: When at least one cluster has a real intent, 0% of loads show `exploring` as the primary intent.
- **SC-016**: When intents tie on cluster count, 100% of loads resolve the tie deterministically using confidence and then the fixed intent order.
- **SC-017**: The interface renders exactly one primary intent message per suggested-plans view and 0 per-cluster messages.

## Assumptions

- "Outbound click" refers to the existing destination-visit interaction, which is the strongest signal for a viewer leaving the catalog toward a provider. No new signal kind is introduced.
- Each corroborating click is attributed to the interest cluster nearest to the clicked plan in the recommendation space, because individual signals are stored against plans rather than clusters.
- Negative-direction explanations use an "avoiding" phrasing for the same intent pattern. The exact Persian copy for negative direction is finalized during planning; the positive copy is fixed by this specification.
- The suggested-plans response keeps its existing plan payload and gains one explanation object per interest cluster. If the current response is flat, cluster grouping is introduced only as far as required to associate each explanation with its cluster.
- The primary-intent count is unweighted: each cluster contributes one vote for its detected intent, regardless of the cluster's confidence or size.
- The primary intent's confidence and message come from the highest-scoring cluster carrying that intent, so the displayed confidence is a real cluster result rather than an average.
- The fixed tie-break order is `cheap`, `value`, `spec_heavy`, `premium`, matching the order in which the real patterns are declared.
- The catalog population for contingency tables is the full set of plans available to the recommendation space in the same request.
- A cluster with no usable candidate set or no corroborating clicks falls back to `exploring` rather than omitting the explanation.
- The existing space version, profile rebuild behavior, and ranking order remain unchanged.
- The defaults in this specification are the production defaults; operators may tune them at runtime.

## Dependencies

- Feature 005 recommendation space, ranking, candidate selection, and interest signals.
- Feature 006 multi-cluster interest state and semantic dimensions.
- The cached recommendation space and its version.
- Existing runtime configuration mechanism for recommendation thresholds.
- Existing Persian user-facing copy conventions.

## Out of Scope

- The `text_specific:<keyword>` pattern and any keyword extraction, stop-word handling, or multilingual title matching.
- Machine-learning or language-model intent classification.
- Changes to the clustering algorithm or cluster count.
- Changes to the feature-005 or feature-006 recommendation space, ranking basis, or signal capture.
- Online A/B measurement of intent-detection quality.
- Frontend redesign beyond rendering the single primary intent message.
