# Feature Specification: Admin Console — Company Approval & Site Data Maintenance

**Feature Branch**: `003-admin-ops-console`

**Created**: 2026-10-27

**Status**: Draft

**Input**: User description: "I want to take the admin side. This section consists of two main parts: company approval and maintaining their sites using the library https://github.com/MhkaPR/domtrack.git. The company approval part is clear. The site maintenance part is as follows: for every site that is approved, its links must be added to the system automatically if it has a sitemap; otherwise, the operator enters them. The selected links, after review in which some are extra and are removed, and this review is done by the operator, enter the capture stage. The capture stage is as follows: the operator, using domtrack installed on their system, clicks a button in the site panel that calls the local domtrack API, and the Chrome page opens for that link and recording begins. After recording ends, the file address on the operator's system is received, and the site uploads it automatically if possible, or with the operator's permission, and it enters the next stage. Table extract stage: in this stage, the uploaded JSON is converted into table JSON and stored as database records. Labeling stage: (optional, disabled by default, but the admin can enable it) in this stage, using the domtrack library on the server with an LLM, the column information and table names are made meaningful. Merge and mapping stage: In this stage, a page opens for the operator that has a large spreadsheet with HandsonTable, and at the top they can switch between tables with a dropdown. They must come and, according to a schema that represents a host or server plan, merge and combine the information and finally connect it to the schema. After this, the system understands from which selector the data should be extracted and how it should be combined with which formula so that the data becomes the desired field. From then on, every time replay is performed to extract information, data will be taken and combined using the same pattern. The next stage is cleaning (the goal is for humans to do the least amount of work): the system cleans the data so that filters can be applied to it. And the data is placed on the main site so that people can use it. In the background, every time period that is available from the admin panel, the system replays the sites to extract the data using the domtrack library and the compare tool, extracts the differences, and updates the data. Every time the failure rate rises, the system sends a notification that such-and-such link needs to be updated, and the operator must go through the above stages again for it. You can see the domtrack documentation through the .venv folder in the domtrack/docs section. **The domtrack library MUST be used as-is for every capability it already provides — capture, replay, record-during-replay, compare, diff, HTML rebuild, table discovery, and LLM table labeling — and none of those capabilities may be reimplemented.**"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Company approval (Priority: P1)

An operator opens the admin console and sees the queue of companies awaiting verification, each with the information needed to decide (company name, representative, domain, phone, and any duplicate-domain warning). The operator reviews a company and records exactly one outcome: **approved**, which makes the company verified and opens its full panel and its site-maintenance lifecycle, or **not approved**, which leaves the company unverified and reopens its registration step for correction. Every decision is written to an append-only decision record: outcome, deciding operator, time, and the note the operator used. The company owner can never set or influence the outcome.

**Why this priority**: Nothing downstream can exist until a company is approved — a site is only maintained once its company is approved. This is the entry gate for the entire feature and delivers value on its own (operators can clear the verification queue).

**Independent Test**: With a pending company in the queue, record an approval and confirm the company becomes verified, its full panel opens, and a decision record exists; repeat with a not-approved outcome and confirm the company stays unverified, its registration step reopens, and a decision record exists.

**Acceptance Scenarios**:

1. **Given** companies awaiting verification, **When** an operator opens the admin console, **Then** the pending companies are listed with the information required to decide.
2. **Given** a pending company, **When** the operator records an approval, **Then** the company becomes verified, its full panel becomes reachable, its site-maintenance lifecycle starts, and an append-only decision record captures the outcome, operator, time, and note.
3. **Given** a pending company, **When** the operator records a not-approved outcome, **Then** the company remains unverified, its registration step reopens as the current step, and an append-only decision record captures the outcome, operator, time, and note.
4. **Given** a company whose normalized domain matches an existing company, **When** the operator reviews it, **Then** a duplicate-domain warning is shown to the operator, no automatic rejection or merge occurs, and resolution remains the operator's decision.
5. **Given** a company owner, **When** they attempt to approve, reject, or otherwise set their own company's verification status, **Then** the attempt is refused because decision recording is restricted to operators.
6. **Given** a company that was approved, **When** onboarding begins, **Then** the company's site enters the site-maintenance lifecycle.

---

### User Story 2 - Site onboarding and link review (Priority: P2)

For an approved company, the operator onboards the company's site. When the site exposes a discoverable sitemap, the system automatically enumerates candidate links from it; when no sitemap is available, the operator enters links manually. The collected links are then presented for operator review, where the operator keeps the useful links and removes the extra ones. Only the kept links proceed to capture.

**Why this priority**: Capture, extraction, and everything after operate on links. Without an operator-curated link set there is nothing to capture, so this is the second gate in the pipeline.

**Independent Test**: Onboard a site with a sitemap and confirm candidate links are auto-discovered; onboard a site without a sitemap and confirm the operator can enter links; in both cases remove some links during review and confirm only the kept links proceed to capture while removed links are excluded.

**Acceptance Scenarios**:

1. **Given** an approved company whose site has a discoverable sitemap, **When** the site is onboarded, **Then** candidate links are automatically added to the system from the sitemap.
2. **Given** an approved company whose site has no sitemap, **When** the site is onboarded, **Then** the operator can enter links manually.
3. **Given** a set of discovered or entered links, **When** the operator reviews them, **Then** the operator can remove individual links and keep the rest.
4. **Given** a completed link review, **When** the review is submitted, **Then** only kept links proceed to the capture stage and removed links are excluded and recorded as removed.

---

### User Story 3 - Operator-driven capture (Priority: P3)

For a kept link, the operator clicks a capture button in the site panel. This calls the **domtrack capture** capability running locally on the operator's own machine: a real Chrome window opens on that link and recording begins (interactive recording — the operator drives the page and ends the recording). domtrack writes the recording as a trace file, reports its location on the operator's system, and the trace is brought into the platform — automatically when the operator's browser permits, otherwise through an operator-confirmed manual upload. The link advances to the next stage only once a trace has been stored.

**Why this priority**: Capture is the point at which real, provider-specific page structure enters the system, and it is domtrack's core feature. It is the first stage that produces the raw artifact every later stage consumes.

**Independent Test**: With domtrack running locally, trigger capture for a kept link and confirm a Chrome window opens on that link and records; confirm that when recording ends the trace file location is reported and the trace is stored against the link, and that the link does not advance without a stored trace.

**Acceptance Scenarios**:

1. **Given** a kept link and domtrack running locally, **When** the operator triggers capture, **Then** domtrack opens a Chrome window on that link and recording begins.
2. **Given** a capture in progress, **When** the operator ends recording, **Then** domtrack writes a trace file and reports its location on the operator's system.
3. **Given** a completed recording, **When** the operator's browser permits automatic transfer, **Then** the trace is uploaded to the platform automatically.
4. **Given** a completed recording and a browser that does not permit automatic transfer, **When** the operator confirms, **Then** the operator can upload the trace manually.
5. **Given** a link whose capture has not produced a stored trace, **When** the pipeline is evaluated, **Then** the link does not advance to the extraction stage.
6. **Given** a stored trace, **When** it is examined, **Then** it is in domtrack's trace format and is associated with its link, the operator who captured it, and the capture time.

---

### User Story 4 - Table extraction (Priority: P4)

An uploaded trace is passed to **domtrack's table extraction**, which discovers the repeated tabular structures in the trace and returns table documents (columns and rows). Those table documents are stored as database records linked to the link and trace. Extraction is browser-free and deterministic: the same trace always yields the same tables.

**Why this priority**: Extraction turns an opaque trace into structured data that can be mapped to plan fields. It is the last purely mechanical stage before human mapping work begins, and it is a domtrack feature used as-is.

**Independent Test**: Upload a trace and confirm domtrack returns one or more table documents and that they are stored as records linked to the capture; re-run extraction on the same trace and confirm the output is identical.

**Acceptance Scenarios**:

1. **Given** a stored trace, **When** extraction runs, **Then** domtrack discovers and returns one or more table documents.
2. **Given** returned table documents, **When** they are persisted, **Then** they are stored as database records linked to their link and trace.
3. **Given** the same trace, **When** extraction is run again, **Then** the returned tables are identical.

---

### User Story 5 - Optional LLM labeling (Priority: P5)

Labeling is disabled by default and enabled only by an admin. When enabled, the system passes the extracted tables to **domtrack's table labeling**, which uses an LLM on the server to give each table a meaningful name/purpose and each column a meaningful label. Labeling is never required: every later stage works whether or not labels exist.

**Why this priority**: It is a domtrack feature that materially improves the mapping stage, but it is explicitly optional and off by default, so it never gates the pipeline.

**Independent Test**: With labeling disabled, confirm extracted tables carry no semantic labels and mapping still works; enable labeling as an admin and confirm table names and column labels become meaningful; disable it again and confirm the pipeline is unaffected.

**Acceptance Scenarios**:

1. **Given** a default configuration, **When** extraction produces tables, **Then** no labeling is applied and the tables carry only their raw structure.
2. **Given** an admin who enables labeling, **When** labeling runs on extracted tables, **Then** table names/purposes and column labels become meaningful.
3. **Given** labeling disabled, **When** the operator maps and publishes, **Then** the pipeline completes exactly as it does with labeling enabled.
4. **Given** an LLM cost ceiling, **When** labeling would exceed it, **Then** labeling stops and the situation is reported rather than silently overspending.

---

### User Story 6 - Merge and mapping to the plan schema (Priority: P6)

The operator opens a mapping workspace: a large spreadsheet view where all extracted tables for the link are available and can be switched between with a dropdown at the top. Working against the plan schema, the operator merges and combines information across tables and connects each resulting value to the corresponding schema field. domtrack's extracted table structure tells us, per column, the path/selector the value came from; the operator supplies the combination formula that turns source values into a schema field. When the operator finishes, the system has captured, for every field, which source selector supplies the data and which formula combines it — the extraction recipe. From then on, every replay re-extracts the data using that same recipe.

**Why this priority**: The recipe is what converts a one-off human mapping into a repeatable, automatable extraction. Without it, scheduled replay (User Story 8) has nothing to run.

**Independent Test**: With several extracted tables for a link and the plan schema, open the mapping workspace, switch between tables, combine fields across tables, connect every required schema field, and confirm a recipe is produced that records a source selector and a combination formula per field; then confirm the link cannot be marked mapped while a required field is unconnected.

**Acceptance Scenarios**:

1. **Given** a link with extracted tables, **When** the operator opens the mapping workspace, **Then** the tables are shown in a spreadsheet view and the operator can switch between them with a dropdown.
2. **Given** multiple extracted tables, **When** the operator maps fields, **Then** the operator can merge and combine information across tables into a single result.
3. **Given** the plan schema, **When** the operator selects the plan type and connects mapped values to the schema, **Then** each connected field records the source selector (from the table's column path) and the combination formula used to produce it.
4. **Given** a completed mapping, **When** the recipe is saved, **Then** subsequent replays re-extract the data using that same recipe.
5. **Given** a mapping in progress, **When** a required schema field is still unconnected, **Then** the link is not marked as mapped.
6. **Given** a saved recipe, **When** the operator reopens the mapping workspace, **Then** the previously connected fields, selectors, and formulas are restored.

---

### User Story 7 - Cleaning and publishing to the main site (Priority: P7)

The system cleans and standardizes the mapped data so that filters can be applied to it, with the goal that humans do the least possible work: cleaning is automatic by default and the operator only intervenes on exceptions. The cleaned data is then published to the main site so that end users can use it.

**Why this priority**: Cleaned, published data is the payoff of the whole pipeline — it is what makes the ingested information usable by end users and filterable.

**Independent Test**: Take mapped data with values that would defeat filtering (inconsistent units, ranges, categories) and confirm the system cleans it so filters can be applied, that the operator is only asked to resolve exceptions, and that the result is published to the main site with its provenance intact.

**Acceptance Scenarios**:

1. **Given** mapped data, **When** cleaning runs, **Then** values are standardized so that filters can be applied to them.
2. **Given** data that can be cleaned automatically, **When** cleaning runs, **Then** no operator action is required.
3. **Given** data the system cannot clean automatically, **When** cleaning runs, **Then** only those exceptions are surfaced to the operator for resolution.
4. **Given** cleaned data, **When** it is published, **Then** it is available on the main site for end users to use.
5. **Given** a published record, **When** it is examined, **Then** it carries provenance linking it to its site, link, trace, and recipe.

---

### User Story 8 - Scheduled replay, diff, and failure alerting (Priority: P8)

In the background, the system re-runs extraction for maintained sites on a period configured from the admin console. It uses **domtrack's compare capability** (replay → record → diff) on the server: it replays each link's stored trace, records the current page as a fresh trace, diffs the two to extract the differences, and updates the published data. The system tracks how often extraction fails per link; when the failure rate rises past a configured threshold, it sends a notification that a specific link needs updating, and the operator re-runs the maintenance stages for that link.

**Why this priority**: This is what keeps the data fresh after the initial build. It is last because it depends on a working recipe and published data from the earlier stories.

**Independent Test**: Configure a replay period, confirm the system replays maintained links on that period, records the current page, diffs it against the previous trace, extracts differences, and updates published data; force a link's failure rate past the threshold and confirm a notification names that link.

**Acceptance Scenarios**:

1. **Given** a configured replay period, **When** the period elapses, **Then** the system replays the maintained links and re-extracts data using their saved recipes.
2. **Given** a replay, **When** the current page is recorded, **Then** domtrack's compare produces the diff between the new recording and the previous trace.
3. **Given** a diff, **When** the differences are applied, **Then** the published data is updated.
4. **Given** a link whose failure rate rises past the configured threshold, **When** the threshold is crossed, **Then** the system sends a notification identifying that link as needing an update.
5. **Given** a link flagged as needing an update, **When** the operator acts, **Then** the operator can re-run the maintenance stages (capture, extract, map, clean, publish) for that link.

---

### Edge Cases

- **Site has no sitemap and the operator enters no links**: the site stays at the onboarding stage; no capture occurs and the operator is told the link set is empty.
- **Sitemap exists but yields no usable links**: the operator can fall back to entering links manually rather than being blocked.
- **domtrack is not running locally**: triggering capture fails with a clear message telling the operator domtrack must be running; the link is not advanced.
- **Browser does not permit automatic transfer**: the flow falls back to an operator-confirmed manual upload rather than losing the trace.
- **Capture produced no trace** (operator cancelled, domtrack crashed): the link does not advance; the failed attempt is recorded.
- **Extraction yields no tables** for a trace: domtrack returns no tables, the link is flagged so the operator knows mapping cannot proceed, and the operator can re-capture (possibly with a different observed subtree).
- **A required schema field is left unconnected**: the link cannot be marked mapped and cannot be published.
- **A source selector that worked before no longer matches** after the provider changes their page: domtrack's replay reports the affected mutations as failed, the affected field fails at replay time, and the failures count toward the link's failure rate.
- **Third-party widgets (chat/support) pollute a trace**: replay's clean mode and third-party detection exclude them so they do not create false differences.
- **Failure rate crosses the threshold and then falls again**: the alert is not repeated for every subsequent replay; it reflects the link's current state.
- **Labeling enabled but LLM unavailable or ceiling reached**: extraction and mapping continue without labels; the operator is informed rather than blocked.
- **Cleaning cannot standardize a value**: only that exception is surfaced; the rest of the record is cleaned and remains publishable.
- **A previously published record disappears from a replay** (listing removed by the provider): the diff reports it as removed and the published data is updated rather than silently keeping stale values.
- **Company rejected after its site is already being maintained**: the company returns to unverified and its maintenance lifecycle is suspended rather than continuing to publish.

## Requirements *(mandatory)*

### Functional Requirements

**domtrack reuse (non-negotiable)**

- **FR-000**: The system MUST use the domtrack library for every capability it already provides, and MUST NOT reimplement any of them. Specifically: page capture and recording (`domtrack capture`), replay (`domtrack replay`), record-during-replay (`domtrack replay --record`), replay-to-record-to-diff comparison (`domtrack compare`), content diffing (`domtrack diff`), browser-free DOM reconstruction (`domtrack html`), tabular-structure discovery (`domtrack tables extract`), and LLM table labeling (`domtrack tables label`). These are consumed either as the domtrack library or through its REST API (`domtrack serve`), whichever fits the stage.
- **FR-000a**: The stored recording artifact MUST be domtrack's native trace file, so that the same trace feeds replay, compare, diff, and table extraction without conversion or bespoke parsing.
- **FR-000b**: Where a stage has no domtrack equivalent (link/sitemap discovery, the mapping workspace and its recipe, cleaning, publishing, scheduling, failure tracking, and notifications), the system MUST implement it, but MUST NOT duplicate anything domtrack already does.

**Company approval (admin console)**

- **FR-001**: The system MUST provide an operator-facing admin console that lists companies awaiting verification together with the information required to decide.
- **FR-002**: An operator MUST be able to record exactly one of two outcomes for a company review — approved or not approved — and each decision MUST be written as an append-only record containing the outcome, the deciding operator, the time, and the operator's note.
- **FR-003**: An approved outcome MUST make the company verified, MUST make its full panel reachable, and MUST start the site-maintenance lifecycle for the company's site; a not-approved outcome MUST leave the company unverified and MUST reopen its registration step for correction.
- **FR-004**: The system MUST show a duplicate-domain warning to the operator when a reviewed company's normalized domain matches an existing company, MUST NOT auto-reject or auto-merge on a domain match, and MUST leave resolution to the operator.
- **FR-005**: The system MUST restrict verification decision recording to operators and MUST refuse any attempt by a company owner to set or influence their own company's verification status.
- **FR-006**: The system MUST NOT modify or remove an existing decision record once written.

**Site onboarding and link review**

- **FR-007**: A site MUST represent a crawl target and MUST be the company's single site — one site per company, identified by the company's registered domain. A company MUST NOT have more than one site in this feature.
- **FR-008**: When a site exposes a discoverable sitemap, the system MUST automatically enumerate candidate links from it; when no sitemap is available, the operator MUST be able to enter links manually.
- **FR-009**: The system MUST present the discovered and entered links for operator review and MUST let the operator remove individual links and keep the rest.
- **FR-010**: Only links kept in review MUST proceed to capture; removed links MUST be excluded and MUST be recorded as removed.
- **FR-011**: When a site has no usable links (no sitemap and none entered, or a sitemap that yields none), the system MUST keep the site at the onboarding stage and MUST inform the operator.

**Operator-driven capture (domtrack capture)**

- **FR-012**: The system MUST let the operator trigger capture for a kept link from the site panel, and triggering capture MUST invoke domtrack's capture capability running locally on the operator's machine, opening a Chrome window on that link and starting recording.
- **FR-013**: Capture MUST support interactive recording (the browser opens, the operator drives the page, and the operator ends the recording), which is domtrack's default non-headless mode; a fixed-duration recording mode MUST also be usable where a link is captured without human interaction.
- **FR-014**: When recording ends, the system MUST receive the trace file's location on the operator's system, and the link MUST NOT advance to extraction until a trace has been stored.
- **FR-015**: The system MUST upload the trace automatically when the operator's browser permits, and MUST otherwise offer an operator-confirmed manual upload.
- **FR-016**: Each stored trace MUST be associated with its link, the operator who captured it, and the capture time, and MUST be stored in domtrack's trace format.
- **FR-017**: When domtrack is unreachable locally, the system MUST report a clear error to the operator and MUST NOT advance the link.

**Table extraction (domtrack tables extract)**

- **FR-018**: The system MUST convert an uploaded trace into table documents by invoking domtrack's table-discovery capability, and MUST store the returned tables (columns and rows, with each column's path/selector and coverage as domtrack reports them) as database records linked to their link and trace.
- **FR-019**: Extraction MUST be deterministic: the same trace MUST always produce the same tables.
- **FR-020**: When domtrack returns no tables, the system MUST flag the link so the operator knows mapping cannot proceed.

**Optional LLM labeling (domtrack tables label)**

- **FR-021**: Labeling MUST be disabled by default and MUST be enabled only by an admin.
- **FR-022**: When labeling is enabled, the system MUST invoke domtrack's table-labeling capability on the server to assign meaningful table names/purposes and meaningful column labels, using the provider and language the admin configures.
- **FR-023**: Labeling MUST be optional: extraction, mapping, cleaning, publishing, and replay MUST all function identically whether or not labels exist.
- **FR-024**: Labeling MUST respect the project's configurable LLM cost ceiling and MUST stop and report rather than silently exceeding it.

**Merge and mapping to the plan schema**

- **FR-025**: The system MUST provide a mapping workspace that shows a link's extracted tables in a spreadsheet view and lets the operator switch between tables with a dropdown.
- **FR-026**: The operator MUST be able to merge and combine information across multiple extracted tables within the workspace.
- **FR-027**: The system MUST map the combined result onto a single plan schema that represents a host or server plan. The schema MUST be defined in code rather than created or edited by users, and it MUST carry a plan-type dimension so that the applicable data is selected per plan type (for example hosting, CDN, virtual server).
- **FR-028**: For every connected schema field, the system MUST record the source selector (derived from the table column's path as reported by domtrack) that supplies the data and the combination formula that produces the field value, together forming the extraction recipe.
- **FR-029**: The system MUST re-extract data on every subsequent replay using the saved recipe, without requiring the operator to re-map.
- **FR-030**: A link MUST NOT be considered mapped while any required schema field is unconnected, and MUST NOT be published in that state.
- **FR-031**: The mapping workspace MUST restore previously saved selectors and formulas when reopened.

**Cleaning and publishing**

- **FR-032**: The system MUST clean and standardize mapped data so that filters can be applied to it.
- **FR-033**: Cleaning MUST be automatic by default, and the system MUST surface only the exceptions it cannot resolve automatically to the operator.
- **FR-034**: The system MUST publish cleaned data to the main site so that end users can use it.
- **FR-035**: Each published record MUST carry provenance linking it to its site, link, trace, and recipe.
- **FR-036**: When a previously published item disappears from a replay, the system MUST update the published data to reflect the removal rather than retaining stale values.

**Scheduled replay, diff, and failure alerting (domtrack compare / diff)**

- **FR-037**: The system MUST re-run extraction for maintained sites on a period that is configurable from the admin console.
- **FR-038**: Replay MUST be performed with domtrack's replay capability, recording the replayed page as a fresh trace and using domtrack's compare/diff capability to extract the differences against the previous trace; the system MUST NOT implement its own replay or diffing.
- **FR-039**: The system MUST apply extracted differences to update the published data.
- **FR-040**: The system MUST track a failure rate per link, derived from the replay failures domtrack reports, and MUST raise a notification identifying a specific link as needing an update when that failure rate rises past a configurable threshold.
- **FR-041**: When a link's failure rate rises past the configured threshold, the system MUST notify the recipients on an admin-configurable recipient list, and MUST deliver each alert both in-app and by email. An admin MUST be able to add and remove recipients.
- **FR-042**: The system MUST let the operator re-run the maintenance stages (capture, extract, map, clean, publish) for a link flagged as needing an update.

**Cross-cutting**

- **FR-043**: Every tunable value in this feature (replay period, failure-rate threshold, labeling toggle, cleaning rules, and similar) MUST be configurable by operators at runtime rather than hard-coded.
- **FR-044**: The system MUST record approvals and rejections, captures, extractions, mappings, cleanings, publishes, replays, and failures as structured, observable events, and MUST mask or omit personal data in logs.
- **FR-045**: The system MUST report a company's crawl-success and failure-rate metrics per provider so operations can act on degradation.
- **FR-046**: This feature MUST NOT implement the payment or charging process, the public search ranking and results, or the ticket system; it consumes their states and hooks only.

### Key Entities *(include if feature involves data)*

- **Operator / Admin**: The actor who approves companies and runs the site-maintenance pipeline. Decisions and pipeline actions are attributed to them. Distinct from company owners.
- **Company**: The provider entity from the company-registration area. This feature consumes its verification state, transitions it through approval, and starts its site-maintenance lifecycle on approval. A company has exactly one site.
- **Site**: The single crawl target for an approved company, identified by the company's registered domain, holding whether it has a sitemap and its maintenance state (onboarding, active, suspended).
- **Link**: A single page address within a site that is a candidate for capture. Carries its review state (kept or removed), its stage in the pipeline, and its failure rate.
- **Trace / Recording**: A domtrack trace file (rrweb-style snapshot plus incremental records) captured for a link, with the file location on the operator's system, its stored artifact, the capturing operator, and the time. The same trace feeds replay, compare, diff, and table extraction.
- **Extracted Table**: A table document domtrack discovered in a trace (columns with their path/selector, coverage, and type; rows keyed by column), stored as records linked to the link and trace.
- **Semantic Label**: The optional, admin-enabled LLM-produced table name/purpose and column labels attached by domtrack's labeling; absent when labeling is disabled.
- **Plan Schema**: The single, code-defined schema representing a host or server plan that mapped data is connected to. It is not user-editable, carries a plan-type dimension (hosting, CDN, virtual server, and similar) that selects which data applies, and is composed of fields that must each be connected before a link is mapped.
- **Extraction Recipe**: The saved mapping for a link: for each schema field, the source selector and the combination formula. Reused by every replay.
- **Published Record**: A cleaned, filterable unit of data placed on the main site, carrying provenance to its site, link, trace, and recipe.
- **Replay Run**: A scheduled domtrack replay of a link's trace that records the current page, diffs it against the previous trace via domtrack compare, and yields updates to published data plus a failure count.
- **Failure Alert / Notification**: A message raised when a link's failure rate crosses the configured threshold, naming the link and prompting the operator to re-run its stages. Delivered in-app and by email to the admin-configurable recipient list.

## domtrack Feature Reuse *(mandatory)*

This table is the contract for FR-000: every stage that has a domtrack equivalent MUST be served by that equivalent, and nothing in the "domtrack feature used" column may be reimplemented.

| Pipeline stage | domtrack feature used | How the platform consumes it |
| --- | --- | --- |
| Capture / record a link | `domtrack capture` (interactive browser recording; fixed-duration headless mode) | Local domtrack REST API (`POST /capture`) called by the site panel; or the local CLI |
| Replay a stored trace | `domtrack replay` (events / mutations / both modes, speed, time policies, third-party clean mode) | domtrack library on the server for scheduled replay |
| Record the replayed page | `domtrack replay --record` (record-during-replay) | Same server-side replay run |
| Diff before/after | `domtrack compare` (replay, record, and diff in one call) and `domtrack diff` | Server-side scheduled run; the diff's added/removed/changed drive data updates |
| Inspect a trace's DOM | `domtrack html` (browser-free DOM reconstruction at a record point) | Operator diagnostics when a link behaves unexpectedly |
| Table extraction | `domtrack tables extract` (browser-free discovery of repeated tabular structures; min rows/cols; de-duplication) | Server-side, producing the stored Extracted Table records |
| Table labeling | `domtrack tables label` (LLM semantic table/column labels; provider and language configurable; dry-run) | Server-side, gated by the admin toggle and the LLM cost ceiling |
| Table display | `domtrack tables show` (plain / markdown / csv rendering) | Optional rendering of labeled tables for operator review and exports |
| Local capture endpoint | `domtrack serve` (REST API exposing capture/replay/compare/diff/html/tables) | The local endpoint the site panel's capture button calls |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of decided company reviews produce exactly one append-only decision record containing the outcome, the deciding operator, the time, and the note, and no existing record is ever modified or removed.
- **SC-002**: An operator can go from opening the admin console to having recorded a company decision in under 2 minutes per company.
- **SC-003**: 100% of approvals make the company verified and start its site-maintenance lifecycle, and 100% of not-approved outcomes leave the company unverified with its registration step reopened.
- **SC-004**: 0% of company owners are able to set or influence their own company's verification status.
- **SC-005**: For 100% of sites with a discoverable sitemap, candidate links are added automatically; for sites without one, the operator can enter links manually in 100% of attempts.
- **SC-006**: 100% of links removed during review are excluded from capture, and 100% of kept links are eligible for capture.
- **SC-007**: 0% of links advance to extraction without a stored trace, and 100% of stored traces are in domtrack's trace format.
- **SC-008**: The same trace produces identical extracted tables in 100% of repeated extractions.
- **SC-009**: 100% of mapped links record a source selector and a combination formula for every connected schema field, and 0 links are published with a required field unconnected.
- **SC-010**: After the first mapping, 100% of replays re-extract data using the saved recipe with no operator re-mapping.
- **SC-011**: At least 90% of mapped records are cleaned and published without any operator intervention, and 100% of exceptions are surfaced to the operator.
- **SC-012**: Maintained sites are replayed within one configured period of the previous replay, and 100% of replays produce a before/after diff that is applied to published data.
- **SC-013**: 100% of links whose failure rate crosses the configured threshold raise a notification naming that link.
- **SC-014**: An operator can complete a full re-run of a flagged link (capture, extract, map, clean, publish) and see the link return to active status.
- **SC-015**: 100% of the tunable values in this feature can be changed by operators at runtime without editing application code.
- **SC-016**: With labeling disabled, the full pipeline completes with 0 dependency on labels; with labeling enabled, tables and columns receive meaningful labels in the large majority of cases.
- **SC-017**: 0 capabilities already provided by domtrack are reimplemented; capture, replay, compare, diff, HTML rebuild, table extraction, and labeling are all served by domtrack in 100% of uses.
- **SC-018**: No log entry produced by this feature contains unmasked personal data.

## Assumptions

- **This feature builds the operator/admin console** that the company-registration feature modeled as an external application; the verification-decision hooks defined there are what this console drives.
- **domtrack is the mandated ingestion engine** and is used as-is; the platform builds only what domtrack does not provide. domtrack runs locally on the operator's machine for human capture (through its REST API or CLI) and on the server as a library for scheduled replay, compare, diff, table extraction, and labeling.
- **The stored artifact is domtrack's trace file**, which is what makes the pipeline composable: the same trace is replayed, diffed, and mined for tables with no format conversion.
- **Company approval is the entry gate for site maintenance**: a site is maintained only while its company is approved and verified.
- **One site per company** (FR-007): a company's site is its registered domain, and site maintenance is onboarded for that single site once the company is approved.
- **"Automatic upload if possible" means the operator's browser reads the trace file domtrack produced locally and transfers it to the platform**; when the browser does not permit this, the operator uploads the file manually. Either way the trace is stored against the link before extraction.
- **The extraction recipe is the durable artifact of mapping**: selectors (from domtrack's table column paths) plus combination formulas per schema field, so a replay reproduces the intended extraction.
- **The plan schema is a single, code-defined schema** (FR-027) that represents a host or server plan and is not editable by users. It carries a plan-type dimension (hosting, CDN, virtual server, and similar); the plan type selects which schema fields and data apply, and the operator maps against the schema for the relevant plan type.
- **Cleaning targets filterability** (consistent units, numbers, ranges, and categories) rather than editorial quality, and is automated first with human handling only for exceptions; it is the one data stage with no domtrack equivalent.
- **Replay, compare, and diff run server-side on a configured period**; the operator is involved only when a link's failure rate crosses the threshold and it must be re-mapped.
- **Labeling is an optional, admin-gated use of domtrack's labeling**, and it never gates any other stage.
- **Failure alerts go to an admin-configurable recipient list** (FR-041), delivered both in-app and by email; an admin can add and remove recipients.
- **Payment/charging, public search ranking and results, the ticket system, and the end-user-facing crawl that serves views are owned elsewhere**; this feature consumes their states and produces clean published data.
- **Operator identity and authentication are provided by the existing login feature**; this feature assumes an authenticated operator actor and does not re-specify authentication.
