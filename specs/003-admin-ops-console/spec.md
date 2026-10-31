# Feature Specification: Admin Console — Company Approval & Automated Site Data Pipeline

**Feature Branch**: `003-admin-ops-console`

**Created**: 2026-10-27

**Status**: Draft — amended 2026-10-31 to the automated pipeline

**Amendment note**: This revision replaces the operator-driven stages of the original draft —
sitemap/manual link entry, local interactive capture on the operator's machine, the Handsontable
merge-and-map workspace with extraction recipes, and formula-based cleaning — with an automated
pipeline: crawl4ai adaptive link discovery, a deterministic-then-LLM link refilter, server-side
headless domtrack capture, domtrack table extraction, LLM table classification, LLM plan-schema
extraction (data only, never formulas), optional domtrack labeling, and compare-driven replay that
re-invokes the LLM only when a change touches a plans table. The operator keeps the company-approval
gate and the runtime budget/threshold controls; the mapping workspace, extraction recipes, and the
formula/cleaning engine are retired. Link discovery runs on the server, and **domtrack runs
server-side for every stage** (capture included) — no domtrack is required on any operator machine.

**Input**: User description: "Automate the site-maintenance pipeline. (1) Extract links with
crawl4ai adaptive crawling (statistical strategy, no embeddings/LLM) — it replaces sitemap.xml — to
find the host/server plans pages. (2) Refilter the extracted links with an LLM that receives only the
link URL, its `h1–h3`, and the page's important section — extracted deterministically from the normal
HTML, with no HTML sent to the model — before any browser capture; the admin owns the price-sensitive
budget. (3) For each kept link, run a server-side headless capture with domtrack and get a trace.
(4) Extract tabular data with domtrack per page (each page independent). (5) Classify each table as a
plans table or not, with a confidence. (6) For plans tables, extract a list of plans as data in a
standard format with an LLM against a Pydantic schema — data, never formulas or selectors. (7) In
replay, detect both content changes and structural changes with domtrack's compare tool; when a
change touches a table that was classified as a plans table, re-run the LLM extraction against the
schema and refresh the data. (8) The module must be resilient to network and other errors. The admin
sets the LLM token budget; when it is exhausted, links that can continue do continue and LLM-gated
work waits until budget is restored. The domtrack library MUST be used as-is for every capability it
already provides — capture, replay, record-during-replay, compare, diff, HTML rebuild, table
discovery, and LLM table labeling — and none of those capabilities may be reimplemented."

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

### User Story 2 - Automated link discovery (crawl4ai adaptive crawling) (Priority: P2)

For an approved company, the system onboards the company's single site by crawling it with **crawl4ai's adaptive crawler using the statistical strategy** — keyword/BM25 statistics, **no embeddings and no LLM** — with the site's registered domain as the seed and a fixed host/server-plans query (a Persian and an English pass). The links harvested from the crawled pages are reduced by a deterministic policy: same-host only, no fragments, query strings stripped, and an extension/segment deny list (scripts, stylesheets, text, JSON/XML, documents, media, fonts, and non-content paths such as blog, docs, support, auth, cart, and legal pages). The survivors are normalized and deduplicated into the candidate link set. This **replaces sitemap.xml discovery entirely**; no sitemap is fetched, parsed, or required.

**Why this priority**: Link discovery is the entry point of the site-maintenance lifecycle and the first place automation removes operator work. A site with no candidate links cannot proceed.

**Independent Test**: Onboard an approved company's site and confirm the system crawls it with the statistical adaptive crawler, returns a deduplicated candidate link set, and excludes denied extensions and path segments; confirm no sitemap request is made.

**Acceptance Scenarios**:

1. **Given** an approved company, **When** its site is onboarded, **Then** the system discovers candidate links by adaptive crawling from the site domain with the statistical strategy, without embeddings or an LLM, and without fetching a sitemap.
2. **Given** harvested links, **When** the deterministic policy is applied, **Then** only same-host, content links survive; denied extensions and path segments are excluded; query strings and fragments are stripped; and the result is deduplicated.
3. **Given** the same site and query, **When** discovery runs again, **Then** the deterministic filtering and normalization produce the same candidate set for the same harvested links.
4. **Given** a site whose crawl yields no candidate links, **When** discovery completes, **Then** the site stays at the onboarding stage and the operator is informed.

---

### User Story 3 - LLM link refilter before capture (Priority: P3)

Before any browser capture, each candidate link is fetched cheaply and reduced **deterministically** — with no LLM — to its URL, its `h1–h3` headings, and its important section: the largest text-density block inside `<main>` or `<article>`. Only that compact, non-HTML summary is sent to an LLM, which judges whether the page is a host/server plans page, returns the plan type it matches, and reports a confidence. The filter is recall-biased: only links that are confidently **not** plans pages are dropped; borderline links are kept and flagged for review, so a provider is never silently lost.

**Why this priority**: Refiltering keeps Chrome work and LLM cost down by discarding non-plans pages before capture, and it is the first stage that needs the LLM budget.

**Independent Test**: Feed a plans page and a non-plans page through the deterministic extraction and the LLM refilter; confirm only the URL, headings, and important section are sent (no HTML), that the plans page is kept with its plan type and confidence, and that a confidently non-plans page is dropped.

**Acceptance Scenarios**:

1. **Given** a candidate link, **When** it is prepared for refiltering, **Then** the model receives only the URL, the `h1–h3` headings, and the important section (the largest text-density block in `<main>`/`<article>`), and never the page HTML.
2. **Given** the model's judgement, **When** the link is confidently not a plans page, **Then** the link is dropped and recorded as not-a-plans-page.
3. **Given** the model's judgement, **When** the link is a plans page or its confidence is not conclusive, **Then** the link is kept (with its plan type and confidence when available) and borderline cases are flagged for review.
4. **Given** the LLM budget is exhausted, **When** a candidate link still needs refiltering, **Then** the link waits in an awaiting-budget state and is retried when budget is restored, without blocking the rest of the pipeline.

---

### User Story 4 - Server-side headless capture (Priority: P4)

For each kept link, the system captures the page **with domtrack running headless on the server** — not on any operator machine. The server opens the link in a headless browser, navigates and waits for the page to settle, scrolls to trigger lazily loaded content, records a fixed duration, and stores the resulting trace as a native domtrack trace artifact. No operator interaction is required, and the link advances only once a trace has been stored.

**Why this priority**: Capture is the point at which real, provider-specific page structure enters the system, and it is the first stage that produces the raw artifact every later stage consumes.

**Independent Test**: With a kept link, confirm the server captures it headlessly, produces a trace in domtrack's format, stores it against the link, and does not advance the link without a stored trace; confirm no operator machine or local domtrack installation is involved.

**Acceptance Scenarios**:

1. **Given** a kept link, **When** capture runs, **Then** the server opens the link in a headless domtrack capture, records a fixed-duration trace, and stores it as a native domtrack trace.
2. **Given** a capture, **When** the page has lazily loaded content, **Then** the capture scrolls to trigger it before recording so the trace contains the full page.
3. **Given** a capture that produces no trace, **When** the pipeline is evaluated, **Then** the link does not advance, the failed attempt is recorded, and the error is surfaced.
4. **Given** a stored trace, **When** it is examined, **Then** it is in domtrack's trace format and is associated with its link and the capture time.

---

### User Story 5 - Table extraction (domtrack tables extract) (Priority: P5)

Each stored trace is passed to **domtrack's table extraction**, which discovers the repeated tabular structures in the trace and returns table documents (columns and rows). Extraction is browser-free and deterministic per trace, and **each page is treated independently** — no cross-page memory or alignment is applied. Returned tables are stored as database records linked to their link and trace.

**Why this priority**: Extracting tables turns an opaque trace into structured data that can be classified and mined for plans, and it is a domtrack feature used as-is.

**Independent Test**: Run extraction on a stored trace and confirm domtrack returns table documents stored as records linked to the link and trace; re-run it and confirm the output is identical.

**Acceptance Scenarios**:

1. **Given** a stored trace, **When** extraction runs, **Then** domtrack discovers and returns one or more table documents.
2. **Given** returned table documents, **When** they are persisted, **Then** they are stored as database records linked to their link and trace.
3. **Given** the same trace, **When** extraction is run again, **Then** the returned tables are identical.

---

### User Story 6 - Table classification with confidence (Priority: P6)

Each extracted table is classified by an LLM as a **plans table** or not, together with the plan type it matches and a **confidence**. Classification is per table and per page: a page may contribute one, several, or no plans tables. The classification is persisted and is the anchor used later by replay to decide whether a detected change is relevant.

**Why this priority**: Classification isolates the plans tables that carry plan data, so the expensive schema extraction and the replay re-extraction run only where they matter.

**Independent Test**: Feed a plans table and a non-plans table to classification and confirm each is labelled with its verdict, plan type, and confidence; confirm a page with three tables where only one is a plans table produces exactly one plans-table classification.

**Acceptance Scenarios**:

1. **Given** an extracted table, **When** classification runs, **Then** the table is recorded as a plans table or not, with its plan type and confidence.
2. **Given** a page with several tables, **When** classification runs, **Then** each table is classified independently and the page may hold zero, one, or several plans-table verdicts.
3. **Given** the LLM budget is exhausted, **When** a table still needs classification, **Then** it waits in an awaiting-budget state and is retried when budget is restored.

---

### User Story 7 - Plan schema extraction (data, not formulas) (Priority: P7)

For each table classified as a plans table, an LLM extracts the plans **as data** against the single, code-defined plan schema and returns a normalized list of plan records in the standard format. The model produces and normalizes the values themselves — units, amounts, and billing periods — for the matched plan type. **No selectors and no formulas are produced or stored**; the schema is the only durable contract. If a table cannot be mapped to the schema, that table is skipped; the page's other mappable tables are still published.

**Why this priority**: This is the value of the whole pipeline — turning a provider's plans table into clean, structured, comparable plan data with no manual mapping.

**Independent Test**: Run schema extraction on a plans table and confirm a normalized list of plan records is returned against the fixed schema; confirm no selectors/formulas are produced and that an unmappable table is skipped while a sibling mappable table is still published.

**Acceptance Scenarios**:

1. **Given** a plans table, **When** schema extraction runs, **Then** the system returns a list of plan records in the standard format, each populated against the schema's fields for its plan type, with normalized amounts and units.
2. **Given** schema extraction, **When** the output is examined, **Then** it contains data only — no selectors and no formulas are produced or stored.
3. **Given** a table that cannot be mapped to the schema, **When** extraction runs, **Then** that table is skipped and mappable tables on the same page are still extracted.
4. **Given** the LLM budget is exhausted, **When** extraction is required, **Then** the work waits in an awaiting-budget state and resumes when budget is restored without blocking capture, extraction, or unchanged-table processing.

---

### User Story 8 - Optional LLM labeling (Priority: P8)

Labeling is disabled by default and enabled only by an admin. When enabled, the system passes the extracted tables to **domtrack's table labeling**, which uses an LLM on the server to give each table a meaningful name/purpose and each column a meaningful label. Labeling is never required: every other stage works whether or not labels exist.

**Why this priority**: It is a domtrack feature that can enrich review, but it is explicitly optional and off by default, so it never gates the pipeline.

**Independent Test**: With labeling disabled, confirm the pipeline completes unchanged; enable it as an admin and confirm tables and columns become meaningfully labelled; disable it again and confirm the pipeline is unaffected.

**Acceptance Scenarios**:

1. **Given** a default configuration, **When** tables are extracted, **Then** no labeling is applied.
2. **Given** an admin who enables labeling, **When** labeling runs, **Then** table names/purposes and column labels become meaningful.
3. **Given** labeling disabled, **When** the pipeline runs, **Then** it completes exactly as with labeling enabled.
4. **Given** the LLM budget is exhausted, **When** labeling would run, **Then** labeling waits rather than overspending.

---

### User Story 9 - Publishing to the main site (Priority: P9)

The extracted plan records are placed on the main site so that end users can use them, carrying provenance to their site, link, trace, and the classification that made them eligible. When a previously published record disappears from a replay, the published data is updated to reflect the removal rather than retaining stale values.

**Why this priority**: Published plan data is the payoff of the whole pipeline and the input to the comparison the main site provides.

**Independent Test**: Publish extracted plan records and confirm they appear on the main site with provenance; remove a plan from the page on a replay and confirm the published record is retired.

**Acceptance Scenarios**:

1. **Given** extracted plan records, **When** they are published, **Then** they are available on the main site for end users to use.
2. **Given** a published record, **When** it is examined, **Then** it carries provenance linking it to its site, link, trace, and the plans-table classification.
3. **Given** a previously published record that disappears from a replay, **When** the diff is applied, **Then** the published data reflects the removal rather than keeping stale values.

---

### User Story 10 - Scheduled replay, change detection, and conditional re-extraction (Priority: P10)

In the background, the system replays maintained sites on a period configured from the admin console using **domtrack's compare capability** (replay → record → diff in one call): it replays each link's stored trace, records the current page as a fresh trace, and diffs the two. Each detected change is classified as a **content change** or a **structural change**. If the change touches a region that was classified as a plans table, the system re-runs the LLM extraction against the schema and refreshes the plan data; if the change is structural (the table moved or its structure changed), the system first re-runs table discovery and re-classifies which table is the plans table on the fresh trace. Changes that do not touch a plans table trigger no LLM work. The system tracks a per-link failure rate; when it rises past a configured threshold, it notifies the admin-configured recipients naming that specific link.

**Why this priority**: This is what keeps the data fresh after the initial build. It is last because it depends on stored traces, classifications, and published data from the earlier stories.

**Independent Test**: Configure a replay period, confirm the system replays maintained links, records the current page, and diffs it; confirm a change to a plans table re-extracts the data while a change elsewhere does not; force a link's failure rate past the threshold and confirm a notification names that link.

**Acceptance Scenarios**:

1. **Given** a configured replay period, **When** the period elapses, **Then** the system replays the maintained links with domtrack's compare (replay, record, diff) and classifies each change as a content change or a structural change.
2. **Given** a detected change that touches a plans table, **When** the change is processed, **Then** the system re-extracts the plan data with the LLM against the schema and updates the published data.
3. **Given** a structural change touching a plans table, **When** it is processed, **Then** the system re-discovers tables on the fresh trace and re-classifies the plans table before re-extracting.
4. **Given** a detected change that does not touch a plans table, **When** it is processed, **Then** no LLM extraction runs.
5. **Given** a link whose failure rate rises past the configured threshold, **When** the threshold is crossed, **Then** the system notifies the admin-configured recipients, identifying that link.
6. **Given** the LLM budget is exhausted, **When** a change requires re-extraction, **Then** the link waits in an awaiting-budget state and is retried when budget is restored.

---

### Edge Cases

- **The adaptive crawl yields no candidate links**: the site stays at the onboarding stage and the operator is informed; no capture occurs.
- **A candidate link is confidently not a plans page**: it is dropped and recorded as not-a-plans-page.
- **A candidate link is borderline (low confidence)**: it is kept and flagged for review rather than being silently dropped.
- **Capture is headless and the page needs interaction** (tabs/accordions hiding content): the trace reflects only the loaded state; such a link is flagged and counts toward the failure rate.
- **Capture produced no trace** (navigation failed, browser crashed): the link does not advance, the failed attempt is recorded, and the error is surfaced.
- **Extraction yields no tables** for a trace: domtrack returns no tables and the link is recorded as having no tables.
- **A table cannot be mapped to the schema**: that table is skipped; the page's other mappable tables are still extracted and published.
- **A region that was a plans table changes structure**: replay re-discovers and re-classifies the page's tables before re-extracting.
- **The LLM budget is exhausted mid-run**: links that can continue do continue (crawl, capture, extraction, unchanged-table processing); only LLM-gated work waits, and the admin is notified.
- **The LLM provider is unreachable or returns an error**: the affected link retries with backoff and is dead-lettered after the retry budget, without taking down the cycle.
- **A network error occurs during crawl, fetch, or capture**: the affected link is retried and, if it keeps failing, is dead-lettered and counted toward the failure rate.
- **Failure rate crosses the threshold and then falls again**: the alert is not repeated for every subsequent replay; it reflects the link's current state.
- **Labeling enabled but LLM unavailable or budget reached**: extraction, classification, publishing, and replay continue without labels.
- **A previously published record disappears from a replay** (plan removed by the provider): the diff reports it as removed and the published data is updated rather than keeping stale values.
- **Company rejected after its site is already being maintained**: the company returns to unverified and its maintenance lifecycle is suspended rather than continuing to publish.

## Requirements *(mandatory)*

### Functional Requirements

**domtrack reuse (non-negotiable)**

- **FR-000**: The system MUST use the domtrack library for every capability it already provides, and MUST NOT reimplement any of them. Specifically: page capture and recording (`domtrack capture`), replay (`domtrack replay`), record-during-replay (`domtrack replay --record`), replay-to-record-to-diff comparison (`domtrack compare`), content diffing (`domtrack diff`), browser-free DOM reconstruction (`domtrack html`), tabular-structure discovery (`domtrack tables extract`), and LLM table labeling (`domtrack tables label`). These are consumed as the domtrack library or through its REST API (`domtrack serve`), whichever fits the stage.
- **FR-000a**: The stored recording artifact MUST be domtrack's native trace file, so that the same trace feeds replay, compare, diff, and table extraction without conversion or bespoke parsing.
- **FR-000b**: Where a stage has no domtrack equivalent (adaptive link discovery, the link refilter, table classification, plan-schema extraction, publishing, scheduling, budget gating, failure tracking, and notifications), the system MUST implement it, but MUST NOT duplicate anything domtrack already does.
- **FR-000c**: domtrack MUST run server-side for every stage, including capture. No domtrack installation on an operator machine is required by this feature.

**Company approval (admin console)**

- **FR-001**: The system MUST provide an operator-facing admin console that lists companies awaiting verification together with the information required to decide.
- **FR-002**: An operator MUST be able to record exactly one of two outcomes for a company review — approved or not approved — and each decision MUST be written as an append-only record containing the outcome, the deciding operator, the time, and the operator's note.
- **FR-003**: An approved outcome MUST make the company verified, MUST make its full panel reachable, and MUST start the site-maintenance lifecycle for the company's site; a not-approved outcome MUST leave the company unverified and MUST reopen its registration step for correction.
- **FR-004**: The system MUST show a duplicate-domain warning to the operator when a reviewed company's normalized domain matches an existing company, MUST NOT auto-reject or auto-merge on a domain match, and MUST leave resolution to the operator.
- **FR-005**: The system MUST restrict verification decision recording to operators and MUST refuse any attempt by a company owner to set or influence their own company's verification status.
- **FR-006**: The system MUST NOT modify or remove an existing decision record once written.

**Automated link discovery (crawl4ai adaptive crawling)**

- **FR-007**: A site MUST represent a crawl target and MUST be the company's single site — one site per company, identified by the company's registered domain.
- **FR-008**: When a site is onboarded, the system MUST discover candidate links by crawling the site domain with crawl4ai's adaptive crawler using the **statistical strategy** (keyword/BM25 statistics only — no embeddings and no LLM) and a configured host/server-plans query. Link discovery MUST replace sitemap discovery; the system MUST NOT fetch, parse, or require a sitemap.
- **FR-009**: The system MUST reduce harvested links with a deterministic policy: same-host only; fragments removed; query strings stripped; a configurable deny list (file extensions such as scripts, stylesheets, text, JSON/XML, documents, media, and fonts, and non-content path segments such as blog, docs, support, auth, cart, and legal pages) excluded; and the result deduplicated and normalized.
- **FR-010**: The system MUST NOT advance any link that has not passed the link refilter (FR-012) and the deterministic policy (FR-009).
- **FR-011**: When a site's crawl yields no candidate links, the system MUST keep the site at the onboarding stage and MUST inform the operator.

**LLM link refilter**

- **FR-012**: For each candidate link, the system MUST derive, deterministically and without an LLM, the link URL, its `h1–h3` headings, and its important section — the largest text-density block inside `<main>` or `<article>` — from the normal HTML returned by the crawler, and MUST send only that summary (never the page HTML) to an LLM.
- **FR-013**: The LLM MUST judge whether the page is a host/server plans page and MUST return the matched plan type (hosting, CDN, virtual server, and similar) and a confidence.
- **FR-014**: The filter MUST be recall-biased: the system MUST drop a link only when the LLM is confidently certain it is not a plans page, and MUST keep and flag borderline links so providers are not silently lost.
- **FR-015**: The system MUST record each link's refilter verdict (kept/dropped, plan type, confidence, and flag) before capture.

**Server-side headless capture (domtrack capture)**

- **FR-016**: The system MUST capture each kept link by invoking domtrack's capture capability **headless on the server**, and MUST NOT require an operator machine or a local domtrack installation.
- **FR-017**: A capture MUST navigate the link, wait for the page to settle, scroll to trigger lazily loaded content, and record for a configured fixed duration, because headless capture requires a fixed duration.
- **FR-018**: A link MUST NOT advance to extraction until a trace has been stored; when a capture produces no trace, the failed attempt MUST be recorded and the error surfaced.
- **FR-019**: Each stored trace MUST be associated with its link and the capture time, and MUST be stored in domtrack's native trace format.

**Table extraction (domtrack tables extract)**

- **FR-020**: The system MUST convert a stored trace into table documents by invoking domtrack's table-discovery capability, and MUST store the returned tables (columns and rows, with each column's path/selector and coverage as domtrack reports them) as database records linked to their link and trace. Each page MUST be processed independently, with no cross-page alignment.
- **FR-021**: Extraction MUST be deterministic: the same trace MUST always produce the same tables.
- **FR-022**: When domtrack returns no tables, the system MUST record the link as having no tables.

**Table classification (plans / not plans)**

- **FR-023**: The system MUST classify each extracted table by an LLM as a plans table or not, together with the matched plan type and a confidence, and MUST persist the verdict against the table.
- **FR-024**: Classification MUST be per table and per page: a page may hold zero, one, or several plans-table verdicts.
- **FR-025**: The persisted classification MUST be the anchor by which replay decides whether a detected change is relevant to plan data.

**Plan schema extraction (data, not formulas)**

- **FR-026**: For each table classified as a plans table, the system MUST extract the plans as data with an LLM against the single plan schema and MUST return a list of plan records in the standard format.
- **FR-027**: The plan schema MUST be a single, code-defined schema (defined in code, edited by hand) that represents a host or server plan and is not editable by users. It MUST carry a plan-type dimension so that the applicable data is selected per plan type (for example hosting, CDN, virtual server).
- **FR-028**: The LLM MUST produce the data values itself, including normalizing amounts, units, and billing periods — the system MUST NOT produce or store source selectors, combination formulas, or any extraction recipe.
- **FR-029**: When a re-extraction is required (initial extraction or replay), the system MUST re-run the LLM schema extraction against the plan data; no formula or selector replay is performed.
- **FR-030**: When a plans table cannot be mapped to the schema, the system MUST skip that table; mappable tables on the same page MUST still be extracted. A published record MUST NOT contain an unpopulated required schema field.
- **FR-031**: Re-extraction MUST be idempotent for an unchanged plans table: the same table MUST yield the same plan records.

**Optional LLM labeling (domtrack tables label)**

- **FR-032**: Labeling MUST be disabled by default and MUST be enabled only by an admin.
- **FR-033**: When labeling is enabled, the system MUST invoke domtrack's table-labeling capability on the server to assign meaningful table names/purposes and meaningful column labels, using the provider and language the admin configures.
- **FR-034**: Labeling MUST be optional: extraction, classification, schema extraction, publishing, and replay MUST all function identically whether or not labels exist.
- **FR-035**: Labeling MUST respect the LLM token budget and MUST wait rather than overspend.

**Publishing**

- **FR-036**: The system MUST publish extracted plan records to the main site so that end users can use them.
- **FR-037**: Each published record MUST carry provenance linking it to its site, link, trace, and the plans-table classification that made it eligible.
- **FR-038**: When a previously published item disappears from a replay, the system MUST update the published data to reflect the removal rather than retaining stale values.

**Scheduled replay, change detection, and conditional re-extraction (domtrack compare / diff)**

- **FR-039**: The system MUST replay maintained sites on a period configurable from the admin console.
- **FR-040**: Replay MUST be performed with domtrack's compare capability (replay, record, and diff in one call) against the previous trace; the system MUST NOT implement its own replay or diffing.
- **FR-041**: The system MUST classify each detected change as a **content change** or a **structural change**.
- **FR-042**: When a detected change touches a region classified as a plans table, the system MUST re-run the LLM schema extraction against the schema and refresh the published plan data; when the change is structural, the system MUST first re-run table discovery and re-classify the plans table on the fresh trace before re-extracting.
- **FR-043**: When a detected change does not touch a plans table, the system MUST NOT run LLM extraction.
- **FR-044**: The system MUST track a failure rate per link, derived from the replay failures domtrack reports, and MUST raise a notification identifying a specific link as needing an update when that failure rate rises past a configurable threshold.
- **FR-045**: When a link's failure rate rises past the configured threshold, the system MUST notify the recipients on an admin-configurable recipient list and MUST deliver each alert in-app. An admin MUST be able to add and remove recipients. Email delivery is explicitly out of scope by project decision.
- **FR-046**: The system MUST let an operator re-run the maintenance stages (crawl, refilter, capture, extract, classify, extract-schema, publish) for a link flagged as needing an update.

**LLM budget gating**

- **FR-047**: An admin MUST be able to set the LLM token budget (per the ledger's period), and the budget MUST apply to every LLM-gated stage (link refilter, table classification, plan schema extraction, and labeling).
- **FR-048**: When the budget is exhausted, the system MUST NOT stall the pipeline: stages that do not need the LLM (crawl, fetch, capture, table extraction, unchanged-table processing, publishing of already-extracted data) MUST continue, and only LLM-gated work MUST enter an awaiting-budget state and resume when budget is restored.
- **FR-049**: The system MUST notify the admin when the budget is exhausted, and MUST attribute LLM spend per link and per table.
- **FR-050**: A retried LLM call MUST NOT be charged twice (an idempotency key MUST guard each logical LLM call).

**Resilience**

- **FR-051**: Each link MUST be processed in isolation so that a failure on one link does not abort the cycle.
- **FR-052**: Network, crawl, fetch, capture, provider, and LLM errors MUST be retried with backoff up to a configured budget, after which the link MUST be dead-lettered and recorded rather than retried indefinitely.
- **FR-053**: A trace row MUST NOT exist without its stored artifact; artifact storage and database writes MUST be ordered and compensated so the two never diverge.

**Cross-cutting**

- **FR-054**: Every tunable value in this feature (crawl query and bounds, deny list, refilter threshold, capture duration, replay period, failure-rate threshold, labeling toggle, LLM token budget, and similar) MUST be configurable by operators at runtime rather than hard-coded.
- **FR-055**: The system MUST record approvals and rejections, discoveries, refilters, captures, extractions, classifications, schema extractions, publishes, replays, and failures as structured, observable events, and MUST mask or omit personal data in logs.
- **FR-056**: The system MUST report a company's crawl-success and failure-rate metrics per provider so operations can act on degradation.
- **FR-057**: This feature MUST NOT implement the payment or charging process, the public search ranking and results, or the ticket system; it consumes their states and hooks only.

### Key Entities *(include if feature involves data)*

- **Operator / Admin**: The actor who approves companies and controls the automated pipeline (budget, thresholds). Decisions and configuration changes are attributed to them. Distinct from company owners.
- **Company**: The provider entity from the company-registration area. This feature consumes its verification state, transitions it through approval, and starts its site-maintenance lifecycle on approval. A company has exactly one site.
- **Site**: The single crawl target for an approved company, identified by the company's registered domain; it holds its maintenance state (onboarding, active, suspended). It no longer holds sitemap state; the domain is the adaptive-crawl seed.
- **Link**: A single page address within a site that is a candidate for maintenance. Carries its discovery state, its refilter verdict (kept/dropped, plan type, confidence, flag), its stage in the pipeline, its budget state (awaiting budget when applicable), and its failure rate.
- **Trace / Recording**: A domtrack trace file (rrweb-style snapshot plus incremental records) captured headlessly on the server for a link, with the stored artifact and the capture time. The same trace feeds replay, compare, diff, and table extraction.
- **Extracted Table**: A table document domtrack discovered in a trace (columns with their path/selector, coverage, and type; rows keyed by column), stored as records linked to the link and trace. Each page is processed independently.
- **Table Classification**: The LLM verdict for an extracted table — plans table or not, the matched plan type, and a confidence — persisted as the anchor replay uses to decide whether a change is relevant.
- **Plan Record**: A normalized plan extracted from a plans table by the LLM against the plan schema (the list of plan data in the standard format). It contains data only — no selectors and no formulas.
- **Plan Schema**: The single, code-defined schema representing a host or server plan that plan records are extracted against. It is not user-editable (edited by hand in code), carries a plan-type dimension (hosting, CDN, virtual server, and similar) that selects which fields apply, and is the only durable contract of extraction.
- **Semantic Label**: The optional, admin-enabled LLM-produced table name/purpose and column labels attached by domtrack's labeling; absent when labeling is disabled.
- **Published Record**: A plan record placed on the main site, carrying provenance to its site, link, trace, and the plans-table classification.
- **Replay Run**: A scheduled domtrack compare run (replay, record, diff) that yields changes classified as content or structural, plus a failure count, from which plan data is conditionally re-extracted and republished.
- **LLM Budget / Spend Ledger**: The admin-set token budget with period-aligned spend and per-link/per-table attribution; LLM-gated work waits when it is exhausted.
- **Failure Alert / Notification**: A message raised when a link's failure rate crosses the configured threshold, naming the link. Delivered in-app to the admin-configurable recipient list.

## domtrack Feature Reuse *(mandatory)*

This table is the contract for FR-000: every stage that has a domtrack equivalent MUST be served by that equivalent, and nothing in the "domtrack feature used" column may be reimplemented.

| Pipeline stage | domtrack feature used | How the platform consumes it |
| --- | --- | --- |
| Capture / record a link (server-side, headless) | `domtrack capture` (fixed-duration headless recording) | domtrack library on the server; the pipeline runs it headless with a fixed duration |
| Replay a stored trace | `domtrack replay` (events / mutations / both modes, speed, time policies, third-party clean mode) | domtrack library on the server for scheduled replay |
| Record the replayed page | `domtrack replay --record` (record-during-replay) | Same server-side replay run |
| Diff before/after | `domtrack compare` (replay, record, and diff in one call) and `domtrack diff` | Server-side scheduled run; the diff's added/removed/changed drive change classification and data updates |
| Inspect a trace's DOM | `domtrack html` (browser-free DOM reconstruction at a record point) | Operator diagnostics when a link behaves unexpectedly |
| Table extraction | `domtrack tables extract` (browser-free discovery of repeated tabular structures; min rows/cols; de-duplication) | Server-side, producing the stored Extracted Table records |
| Table labeling | `domtrack tables label` (LLM semantic table/column labels; provider and language configurable; dry-run) | Server-side, gated by the admin toggle and the LLM token budget |
| Table display | `domtrack tables show` (plain / markdown / csv rendering) | Optional rendering of labeled tables for operator review and exports |
| REST endpoint | `domtrack serve` (REST API exposing capture/replay/compare/diff/html/tables) | Available server-side for diagnostics and integration |

**No domtrack equivalent (implemented by this feature, not duplicating domtrack):** adaptive link
discovery (crawl4ai), the deterministic link policy and LLM link refilter, table classification,
plan-schema extraction, publishing, scheduling, budget gating, failure tracking, and notifications.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of decided company reviews produce exactly one append-only decision record containing the outcome, the deciding operator, the time, and the note, and no existing record is ever modified or removed.
- **SC-002**: An operator can go from opening the admin console to having recorded a company decision in under 2 minutes per company.
- **SC-003**: 100% of approvals make the company verified and start its site-maintenance lifecycle, and 100% of not-approved outcomes leave the company unverified with its registration step reopened.
- **SC-004**: 0% of company owners are able to set or influence their own company's verification status.
- **SC-005**: 100% of onboarded sites discover candidate links by adaptive crawling with the statistical strategy (no embeddings, no LLM) and 0 sites fetch or require a sitemap.
- **SC-006**: 100% of harvested links pass the deterministic policy (same-host; denied extensions and path segments removed; fragments and query strings stripped; deduplicated) before refiltering.
- **SC-007**: 0% of links send page HTML to the refilter model, and 100% of refilter inputs are limited to the URL, `h1–h3`, and the important section; only confidently non-plans links are dropped.
- **SC-008**: 100% of kept links are captured headlessly on the server, and 0% require an operator machine or a local domtrack installation.
- **SC-009**: 0% of links advance to extraction without a stored trace, and 100% of stored traces are in domtrack's trace format.
- **SC-010**: The same trace produces identical extracted tables in 100% of repeated extractions, and each page is processed independently.
- **SC-011**: 100% of extracted tables receive a plans/not-plans verdict with a confidence, and 100% of plans tables are extracted to schema-shaped plan records.
- **SC-012**: 0 selectors and 0 formulas are produced or stored by extraction; 100% of plan records are data in the standard schema format.
- **SC-013**: At least 90% of plans tables are extracted to schema-shaped plan records without operator intervention, and 100% of tables that cannot be mapped are skipped per-table without dropping their page's mappable tables.
- **SC-014**: Maintained sites are replayed within one configured period of the previous replay, and 100% of replays produce a before/after diff whose changes are classified as content or structural.
- **SC-015**: 100% of changes touching a plans table trigger LLM re-extraction, and 0 changes that do not touch a plans table trigger LLM work.
- **SC-016**: When the LLM budget is exhausted, 100% of non-LLM stages continue and 100% of LLM-gated work waits and resumes when budget is restored, with the admin notified.
- **SC-017**: 100% of links whose failure rate crosses the configured threshold raise a notification naming that link, and 100% of links that exhaust their retries are dead-lettered rather than retried indefinitely.
- **SC-018**: 100% of the tunable values in this feature can be changed by operators at runtime without editing application code.
- **SC-019**: With labeling disabled, the full pipeline completes with 0 dependency on labels; with labeling enabled, tables and columns receive meaningful labels in the large majority of cases.
- **SC-020**: 0 capabilities already provided by domtrack are reimplemented; capture, replay, compare, diff, HTML rebuild, table extraction, and labeling are all served by domtrack in 100% of uses.
- **SC-021**: No log entry produced by this feature contains unmasked personal data.

## Assumptions

- **This feature builds the operator/admin console** that the company-registration feature modeled as an external application; the verification-decision hooks defined there are what this console drives.
- **domtrack is the mandated ingestion engine** and is used as-is; the platform builds only what domtrack does not provide. **domtrack runs server-side for every stage, including capture** — headless with a fixed duration — so no operator machine and no local installation is required.
- **crawl4ai adaptive crawling (statistical strategy) is the link-discovery engine** and replaces sitemap discovery; it uses keyword statistics only (no embeddings, no LLM), and its output links are reduced by a deterministic policy before refiltering.
- **The link refilter is deterministic-then-LLM**: the URL, `h1–h3`, and the important section (largest text-density block in `<main>`/`<article>`) are derived without an LLM; only that summary reaches the model.
- **The stored artifact is domtrack's trace file**, which is what makes the pipeline composable: the same trace is replayed, diffed, and mined for tables with no format conversion.
- **Company approval is the entry gate for site maintenance**: a site is maintained only while its company is approved and verified.
- **One site per company** (FR-007): a company's site is its registered domain, and it is onboarded for that single site once the company is approved.
- **The plan schema is a single, code-defined schema** (FR-027) that represents a host or server plan and is not editable by users; the admin edits it by hand in code. It carries a plan-type dimension (hosting, CDN, virtual server, and similar); the plan type selects which fields and data apply.
- **Extraction produces data, not recipes** (FR-028): the LLM emits normalized plan records directly; there is no selector/formula recipe and no formula-cleaning engine. Normalization (amounts, units, billing periods) happens in the LLM extraction.
- **Replay, compare, and diff run server-side on a configured period**; LLM work in replay runs only when a change touches a plans table, and structural changes trigger re-discovery and re-classification first.
- **The admin owns the LLM token budget** (FR-047); when it is exhausted, non-LLM stages continue and LLM-gated work waits rather than failing the cycle.
- **Labeling is an optional, admin-gated use of domtrack's labeling**, and it never gates any other stage.
- **Failure alerts go to an admin-configurable recipient list** (FR-045), delivered in-app only (email is out of scope by project decision); an admin can add and remove recipients.
- **Payment/charging, public search ranking and results, the ticket system, and the end-user-facing crawl that serves views are owned elsewhere**; this feature consumes their states and produces clean published data.
- **Operator identity and authentication are provided by the existing login feature**; this feature assumes an authenticated operator actor and does not re-specify authentication.
