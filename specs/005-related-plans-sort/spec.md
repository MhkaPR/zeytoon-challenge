# Feature Specification: Personalized Related Plans Ordering

**Feature Branch**: `005-related-plans-sort`

**Created**: 2026-11-06

**Status**: Draft

**Input**: User description: "Add a 'related plans' option to the catalog sort section, make it the default, and order plans by the viewer's demonstrated intent. Most viewers are anonymous, so intent is tracked per device and attached to the account on login."

## Clarifications

### Session 2026-11-06

- Q: Should the company catalogue page also default to the related order, or only offer it as a sort option? → A: Default to related order.
- Q: How long should an inactive viewer's interest history be kept before it is deleted? → A: 180 days of inactivity.
- Q: Should an explicit cheapest/most-expensive choice persist on the next visit, or should every new visit start on related? → A: Every new visit starts on related.
- Q: What is the maximum number of interest signals one viewer may contribute within a minute before further signals are ignored? → A: 30 signals per minute per viewer.
- Q: What should the sort option be labeled in the UI? → A: «پیشنهاد برای شما» (recommended for you).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Anonymous visitor sees a personalized default order (Priority: P1)

A visitor who is not signed in opens the main catalog. Instead of a fixed order (newest, cheapest, or most expensive), the list is ordered by what that visitor has shown interest in so far: which plans they opened details for, which provider pages they visited, and what they searched for. The order is remembered for that device on later visits, even though the visitor never signs in.

**Why this priority**: This is the core of the feature. It delivers value on its own without accounts, and it is the path most visitors will experience.

**Independent Test**: On a fresh device, open the main catalog and record the order. Interact with several plans of one type, reload, and confirm the order shifts toward that type while remaining deterministic when no new interest is recorded.

**Acceptance Scenarios**:

1. **Given** a first-ever visitor with no recorded interest, **When** the catalog loads, **Then** the default order is a stable, deterministic order that is identical for every first-ever visitor and is clearly identified as "related plans".
2. **Given** a visitor who has viewed details of plans of one type, **When** the catalog loads again, **Then** plans of that type rank higher than they did before.
3. **Given** a visitor who has taken no new action, **When** they reload the catalog, **Then** the order is unchanged.
4. **Given** the sort control, **When** the visitor opens it, **Then** «پیشنهاد برای شما» is listed first and selected by default.

---

### User Story 2 - Interest signals refine the order (Priority: P1)

While browsing, the visitor generates interest signals: opening a plan's destination page (strongest), opening plan details (moderate), and the first page of results for a search they typed (weaker). These signals accumulate so repeated interest moves the order further, and a signal that the visitor clearly rejects moves it away.

**Why this priority**: Without signals the default order never changes, so signal capture is what makes the feature more than a static list.

**Independent Test**: Send each signal type for a chosen plan, reload, and confirm the order moves toward the chosen plan's attributes; confirm the destination-page signal moves the order more than a search-result signal for the same plan.

**Acceptance Scenarios**:

1. **Given** a visitor who opened a plan's destination page, **When** the catalog loads next, **Then** that plan and similar plans rank higher, and the effect is stronger than the same action on details only.
2. **Given** a visitor who searched and saw a first page of matching results, **When** the catalog loads next, **Then** the order shifts toward those plans, but by less than a details view or a destination-page visit.
3. **Given** a search result page with several matching plans, **When** the search-impression signal is recorded, **Then** it is recorded once as a single combined influence for that search rather than one full-strength influence per result.
4. **Given** repeated identical signals, **When** the catalog loads, **Then** the influence does not grow without bound.

---

### User Story 3 - Interest carries into the account on login (Priority: P2)

A visitor who has been browsing anonymously signs in. If the account has no prior interest history, the device's history becomes the account's history, and the account continues to receive personalized ordering from then on. If the account already has its own history, the account's history takes precedence and the device adopts it. When the visitor signs out, the device's stored history is cleared for privacy, while the account keeps its history for the next sign-in.

**Why this priority**: This connects the anonymous and signed-in experiences. It is secondary to the anonymous path because it only matters to visitors who sign in.

**Independent Test**: Browsing anonymously, sign in with a fresh account and confirm the same order continues. Sign out and confirm the device starts cold. Sign in again with the same account and confirm the account's order returns. Repeat with an account that already has history and confirm the account's order wins.

**Acceptance Scenarios**:

1. **Given** a device with recorded interest and an account with none, **When** the visitor signs in, **Then** the account adopts the device's interest and the catalog order is continuous.
2. **Given** a device with recorded interest and an account that already has interest, **When** the visitor signs in, **Then** the account's interest wins, the device follows the account, and the device's previous anonymous interest is discarded.
3. **Given** a signed-in visitor, **When** they sign out, **Then** the device's stored interest and device association are cleared and the next anonymous visit starts cold.
4. **Given** the sign-in hand-off, **When** it completes, **Then** the merge is performed once by the platform as part of sign-in, not by a separate user action, and the resulting history is not split across two identities.

---

### User Story 4 - Existing sort behavior and search relevance are preserved (Priority: P2)

A visitor who wants a specific order still gets it. Choosing "cheapest" or "most expensive" orders the whole result set by price as before, and returning to the default brings back the related order. On the search results page, the visitor sees results ordered by how well they match the typed query; only price-based sorts are offered there, so recommendations never override search relevance.

**Why this priority**: The feature must not regress the existing comparator or make search results worse.

**Independent Test**: On the catalog, choose cheapest and confirm strictly ascending prices; choose most expensive and confirm descending; return to related and confirm the personalized order. On the search page, type a query and confirm result relevance ordering and that no related option is offered.

**Acceptance Scenarios**:

1. **Given** the catalog, **When** the visitor chooses cheapest, **Then** all results are ordered by ascending price as before.
2. **Given** the catalog, **When** the visitor chooses most expensive, **Then** all results are ordered by descending price as before.
3. **Given** the catalog with a non-default sort selected, **When** the visitor returns to related, **Then** the related order is restored.
4. **Given** the search results page with a typed query, **When** results load, **Then** they are ordered by query relevance and the sort control offers only price-based options.
5. **Given** active catalog filters or a selected plan type, **When** related ordering applies, **Then** only plans matching those filters are ordered.

---

### Edge Cases

- A first-ever visitor has no signals: the related order is deterministic and identical for all such visitors.
- A plan lacks some attributes (for example a CDN plan has no processor or memory): only attributes the plan actually declares influence its rank, so a plan is never penalized for attributes it does not have.
- A new plan is published after visitor interest exists: it is eligible for recommendation without requiring existing interest.
- A plan is unpublished or retired: it no longer appears regardless of recorded interest.
- The catalog contains fewer than two matching plans: the order is trivial and no error occurs.
- The visitor clears device storage or uses a different device or browser: they start cold with no error.
- A shared device is used by two anonymous people: their interests mix until sign-in or sign-out resets the device.
- The visitor never interacts: the order stays at the cold-start default.
- A signal is sent after sign-out: it must not resurrect the cleared device history in a way that mixes with the previous account.
- A signal arrives around the moment of sign-in: the platform must apply it to exactly one identity, never both.
- The visitor pages through results: consecutive pages contain no duplicated plans while the interest state is unchanged.
- A search returns no results or an empty query: no search-impression signal is recorded.
- Only the first page of search results sends an impression signal; later pages do not.
- Automated traffic without a stable device identity: it receives the cold-start order and does not corrupt a real person's history.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The main catalog MUST offer a sort option labeled «پیشنهاد برای شما» and MUST select it by default when no explicit sort is requested.
- **FR-002**: The related order MUST reflect the accumulated interest of the current viewer, whether anonymous (device-scoped) or signed in (account-scoped).
- **FR-003**: Anonymous interest MUST be scoped to the device and MUST persist across separate visits from that device without sign-in.
- **FR-004**: The system MUST accept three interest signal types: visiting a plan's destination page (strongest), opening plan details (moderate), and the first page of results for a search the visitor typed (weakest).
- **FR-005**: The destination-page signal MUST influence the order more than the details signal, and the details signal MUST influence it more than the search-impression signal.
- **FR-006**: A search-impression signal covering multiple results MUST be recorded as one combined influence for that search, not as a full-strength influence per result.
- **FR-007**: Repeated identical signals MUST have diminishing influence: the hundredth identical signal MUST change the order no more than the tenth.
- **FR-008**: On sign-in, if the account has no interest history, the account MUST adopt the device's history; if the account has history, the account's history MUST take precedence and the device MUST follow the account.
- **FR-009**: The sign-in hand-off MUST be performed by the platform as part of sign-in and MUST result in interest being attached to exactly one identity.
- **FR-010**: On sign-out, the device's stored interest and its device association MUST be cleared, and the account's history MUST be retained.
- **FR-011**: The order MUST be computed over the entire set of plans matching the active filters and tab, not only the visible page.
- **FR-012**: The order MUST be deterministic: viewers with equal interest state see the same relative order, and unchanged interest state produces an unchanged order across reloads.
- **FR-013**: Consecutive pages in one browsing session MUST NOT repeat plans while the interest state is unchanged.
- **FR-014**: The existing cheapest and most-expensive options MUST keep their current price-based behavior.
- **FR-015**: The search results page MUST order by query relevance and MUST offer only price-based sort options; the related option MUST NOT be presented there.
- **FR-016**: A plan that does not declare an attribute MUST NOT be penalized for that attribute when compared with plans that do declare it.
- **FR-017**: A plan's destination page, details view, and search matching MUST remain available to visitors who never interact beyond viewing.
- **FR-018**: Signal submission MUST be the only action the visitor's client performs to influence recommendations; the sign-in hand-off MUST NOT require a client-initiated request.
- **FR-019**: Signal submission MUST accept signals from both anonymous and signed-in visitors and MUST ignore any signals beyond 30 per viewer per minute.
- **FR-020**: The cold-start related order MUST be the same for every viewer with no recorded interest.
- **FR-021**: The related sort MUST be the default on both the main catalog and the company catalog page; it MUST NOT be offered or applied on the search results page.
- **FR-022**: A viewer's interest history MUST NOT be displayed to them or shared with another account; it MUST influence ordering only.
- **FR-023**: Interest profiles and their recorded signals MUST be deleted after 180 days without a new signal.
- **FR-024**: An explicit cheapest or most-expensive choice MUST apply only to the current view and MUST NOT persist; every new catalogue visit MUST start on related.

### Key Entities *(include if feature involves data)*

- **Interest profile**: The accumulated preference of one viewer, with an anonymous device-scoped identity or an account-scoped identity. Holds the preference position, its uncertainty, the number of signals absorbed, and (after sign-in) a link to the account that absorbed a device profile.
- **Interest signal**: A single recorded interaction attributed to one interest profile. Carries the signal type and the plan or set of plans it refers to.
- **Plan attribute profile**: The set of comparable attributes a plan declares (for example price, capacity, resources, location, operating system), used to decide similarity with a viewer's interest. Attributes a plan does not declare are excluded from comparison.
- **Sort selection**: The viewer's current ordering choice for the catalog. Related is the default; cheapest and most expensive are explicit choices.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of catalog loads without an explicit sort present the related order as the default selection.
- **SC-002**: After a visitor records three destination-page visits on plans of one type, that type ranks higher on the next catalog load in every observed case.
- **SC-003**: A device with no new activity sees an identical catalog order on repeated loads within the same session.
- **SC-004**: After sign-out, the next anonymous visit from that device starts at the cold-start order, and re-signing in restores the account's order.
- **SC-005**: After sign-in with an account that has history, the account's order is shown and no interest is attributed to two identities.
- **SC-006**: On the search results page, results remain query-relevance ordered and the related option is absent in 100% of loads.
- **SC-007**: Paging through a session's results yields zero duplicated plans while interest state is unchanged.
- **SC-008**: Choosing cheapest or most expensive yields strictly ordered prices in 100% of observed loads.
- **SC-009**: Two first-ever devices loading the catalog with no interest see the same order.

## Assumptions

- "Main catalog" means the pricing/catalog section of the home page; the company catalog page also defaults to related, and the search results page does not offer it.
- Anonymous identity is a random, opaque device identifier; no fingerprinting or personal data is used.
- Anonymous interest does not sync across devices; cross-device continuity only exists after sign-in.
- Interest profiles and their signals are deleted after 180 days of inactivity.
- Sort choices are not stored per viewer; only the current view reflects an explicit price sort.
- The internal term "related order" is presented to users as «پیشنهاد برای شما»; the two terms refer to the same behaviour.
- Signals are best-effort: a lost signal slightly delays personalization but never breaks the order.
- The search-impression signal applies to the first page of results for a submitted query only; later pages and empty queries produce no signal.
- Ranking compares only attributes a plan declares; plans of different types are compared through their shared declared attributes.
- Default retention and expiry, performance expectations, and abuse resistance follow the product's existing standards.
- The feature is validated manually by the team for this iteration; no automated success-measurement pipeline is in scope.

## Dependencies

- The existing published-plan catalog and its filtering, tab, and pagination behavior.
- The existing sign-in and sign-out flow, which is where the profile hand-off and device reset occur.
- The existing device identity maintained by the platform across visits.
