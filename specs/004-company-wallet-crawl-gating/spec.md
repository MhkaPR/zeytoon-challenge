# Feature Specification: Company Wallet and Crawl Eligibility

**Feature Branch**: `[004-company-wallet-crawl-gating]`

**Created**: 2026-11-02

**Status**: Draft

**Input**: User description: "Remove user email; replace company charge/crawl flags with a company wallet; keep extracted plans private until charge eligibility; when funds are insufficient unpublish all company plans and stop its crawling and replay; discover new domain links and allow manual remaining links; clarify crawl query, URL hash, source, trace byte size, and natural key; show the user's phone in full in frontend and backend displays; show published plans on the main and other required pages. The wallet is implemented in this project, the payment library handles Iranian providers such as Zibal, and the required company wallet amount is configured through django-constance and Django admin. Item 11 was left blank."

**Architecture clarification**: Pipeline domain code and data must live in a dedicated Django
`pipeline` app, separate from `admin_console`, which is reserved for operator/admin APIs,
authorization, and presentation entry points. Operator endpoints call pipeline
behavior through a declared interface; `admin_console` must not own crawler, extraction,
capture, replay, pipeline state, or pipeline model implementations.
This includes moving the existing `llm.py`, pipeline models, tasks, services, discovery,
capture/extraction and replay adapters, schemas, classifiers, events, constants, artifacts,
admin registrations, migrations, and pipeline tests into `pipeline`. Split mixed
`admin_console/services.py`: approval/verification orchestration stays in the console, while
pipeline workflows move. Keep operator HTTP routes and request validation in `admin_console`,
but refactor them to call `pipeline.interfaces` without importing pipeline internals.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Company wallet controls plan visibility (Priority: P1)

A company owner can fund and review the company wallet. The wallet is owned by this product; the payment library supports payments through Iranian providers such as Zibal. A configured minimum amount determines whether the company may publish plans. Extracted plan data may be retained for operator review, but end users must not see it until the company meets the requirement. If the wallet balance falls below the configured amount, every public plan for that company becomes unavailable and the company is excluded from crawling and replay until eligibility is restored.

**Why this priority**: Public listings without the required company payment violate the core provider business rule and can expose plans after a company's balance is depleted.

**Independent Test**: Exercise a company with sufficient funds, then reduce its wallet below the required amount; verify plan visibility and crawl/replay eligibility change together and that restoring eligibility makes eligible plans available again.

**Acceptance Scenarios**:

1. **Given** a company has extracted valid plans but has not met the required charge, **When** a public page requests plans, **Then** none of that company's plans are returned to end users.
2. **Given** a company meets the required charge, **When** its plans pass existing publication quality checks, **Then** those plans appear in the public catalog and required plan pages.
3. **Given** a company becomes ineligible because its wallet has insufficient funds, **When** background eligibility processing runs, **Then** all of its public plans are withdrawn and its crawls and replays are skipped.
4. **Given** an ineligible company's wallet later meets the required charge, **When** eligibility is reevaluated, **Then** crawling and replay may resume and only still-valid, quality-approved plans become public.
5. **Given** a payment or wallet operation is repeated for the same payment reference, **When** the result is processed more than once, **Then** the company is charged at most once for that reference.

### User Story 2 - Refresh and complete a company's discovered links (Priority: P1)

An operator can refresh link discovery for an eligible company to find pages added since the previous crawl. A company can also submit its remaining plan-page links so that discovery does not depend on the crawler finding every page.

**Why this priority**: New or missed plan pages must enter the same reviewed extraction pipeline without duplicating existing links.

**Independent Test**: Run discovery twice after adding a page to the domain, then submit a manually supplied URL; verify new links are added, existing links are not duplicated, and both link sources can continue through the normal pipeline.

**Acceptance Scenarios**:

1. **Given** an eligible company has an existing discovered link set, **When** an operator starts a new discovery run, **Then** newly found same-domain plan candidates are added without duplicating existing URLs.
2. **Given** an eligible company has a plan page that automated discovery missed, **When** the company submits that URL, **Then** it is validated against the company's domain policy and added to the link review/pipeline list.
3. **Given** a company is financially ineligible, **When** an operator or scheduled process requests discovery, **Then** no new crawl is performed and the reason is visible to the operator.
4. **Given** a URL already exists for the site, **When** the same URL is discovered or submitted again, **Then** the existing link record is reused rather than duplicated.

### User Story 3 - Phone-only account and full phone display (Priority: P2)

An end user does not need an email address to register or use the account, and sees their phone number in full in frontend and backend displays. Where company phone numbers are displayed to users, they are also shown in full. End-user pages show provider plans only when the company is eligible and the plans are published.

**Why this priority**: The product uses phone-based identity, and public plan and contact data must follow the company's payment eligibility.

**Independent Test**: Create and authenticate a phone-only account, inspect frontend and backend displays, and verify no email is requested or exposed and displayed phone numbers are complete.

**Acceptance Scenarios**:

1. **Given** a user registers or signs in using a phone number, **When** account data is saved or returned, **Then** an email address is neither required nor represented as user profile data.
2. **Given** a user's phone number is displayed in the frontend or backend, **When** the page or response is rendered for an authorized viewer, **Then** the complete phone number is shown without masking.
3. **Given** a company has eligible published plans, **When** an end user visits the main page, search/results, or relevant plan detail/comparison pages, **Then** those plans are available consistently on each applicable page.
4. **Given** those plans are withdrawn for insufficient wallet balance, **When** any public plan page is requested, **Then** the plans are not exposed through an alternate page or cached result.

### Edge Cases

- A payment callback is delayed, duplicated, rejected, or arrives after the company was archived.
- A wallet balance changes during a crawl, publication, or public read; the public visibility decision must use the current authoritative eligibility result.
- A company's wallet is exactly at the required amount, below zero, zero, or insufficient for the next required charge.
- Some plans are already public when a company becomes ineligible; all public plans for that company must be withdrawn as one logically complete eligibility change.
- Wallet recovery occurs while a previous crawl or replay task is still queued; the work must not be duplicated or run concurrently for the same link.
- Discovery returns only URLs already known, or a manually supplied URL is off-domain, malformed, or duplicated.
- A company submits an existing URL with a different scheme, fragment, query string, or trailing slash.
- A phone number is malformed or unavailable; the display must communicate that state without substituting another user's number.
- A stale public search index or page cache still contains a plan after it has been withdrawn.
- Item 11 in the reported bug list has no description and is not included in the feature scope until supplied.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The user account MUST NOT store an email address; registration, authentication, and profile responses MUST use the existing phone-based identity only.
- **FR-002**: The system MUST maintain a company-owned wallet and its balance and transaction history in this product. It MUST use the payment library only to accept and confirm payments through supported Iranian providers, including Zibal.
- **FR-003**: The system MUST provide an administrator-configurable required company wallet amount through django-constance and Django admin. A company is financially eligible when its authoritative wallet balance meets or exceeds this configured amount.
- **FR-004**: The system MUST allow extraction and internal retention of valid plan records independently from their public visibility; extracted or successfully processed plans MUST remain private until the company meets the charge eligibility requirement.
- **FR-005**: The system MUST withdraw every public plan belonging to a company when its wallet no longer meets the applicable charge requirement, without deleting retained extraction or provenance records.
- **FR-006**: The system MUST prevent end users from retrieving a company's withdrawn plans through the main page, search/results, plan detail, comparison, cached responses, or any other public plan surface.
- **FR-007**: The system MUST exclude financially ineligible companies from automated link discovery, capture, crawling, and replay, including scheduled background work.
- **FR-008**: The system MUST reevaluate company eligibility after relevant wallet changes and restore public plan availability and crawl/replay eligibility only when the applicable requirements are met.
- **FR-009**: Payment confirmation and wallet crediting MUST be idempotent so a repeated provider callback or payment reference cannot credit a company more than once.
- **FR-010**: The system MUST support an operator-triggered discovery refresh that searches the company's registered domain for newly added plan links after initial discovery.
- **FR-011**: The system MUST permit an authorized company user to submit additional same-domain plan URLs for review and processing.
- **FR-012**: Automated and manual link additions MUST share domain, URL, and duplicate validation; adding an already-known URL MUST reuse the existing link rather than create a duplicate.
- **FR-013**: The system MUST retain a way to distinguish manually supplied links from automatically discovered links for review, troubleshooting, and reporting.
- **FR-014**: The complete phone number MUST be shown in authorized frontend and backend user-facing displays, including the user's account/profile views. Phone numbers MUST NOT be masked in these displays. Structured logs and other operational telemetry MUST continue to follow the existing requirement to mask or omit full phone numbers.
- **FR-015**: Once eligible and published, plans MUST be available on the main page and every applicable search, detail, and comparison page, with consistent visibility across those surfaces.
- **FR-016**: The system MUST remove the unused per-site crawl-query value from the site record; crawl queries MUST be managed as discovery configuration unless a future requirement defines a per-site override.
- **FR-017**: The system MUST document the purpose of link URL hashes (stable normalization and per-site deduplication), link source (manual versus automated provenance), trace byte size (stored-artifact size observability), and plan natural keys (stable plan identity for upsert and retirement) in the relevant operator or developer documentation.
- **FR-018**: The system MUST record eligibility changes, payment/wallet outcomes, discovery refreshes, manual link submissions, plan withdrawals/restorations, and skipped crawl/replay work as auditable events without logging full phone numbers or payment secrets.
- **FR-019**: The system MUST expose the reason a company is ineligible to authorized company users and operators, including insufficient balance or pending payment confirmation.
- **FR-020**: The system MUST preserve existing authorization boundaries: company users may submit links only for companies they own, and operators may trigger or inspect company-wide discovery and eligibility operations only with their existing authorized role.
- **FR-021**: The system MUST keep pipeline domain code and pipeline-owned data in a dedicated Django `pipeline` app separate from the `admin_console` app. `admin_console` MUST be limited to operator/admin APIs, authorization, and presentation, and MUST invoke pipeline operations through the pipeline's declared interface.

### Key Entities *(include if feature involves data)*

- **Company wallet**: The authoritative balance and transaction history associated with one company, maintained by this product and credited after confirmed payments.
- **Charge eligibility**: The current result of comparing the company's wallet state with the applicable plan charge requirement; it gates public visibility and background crawling.
- **Published plan**: A quality-approved plan record available to end users only while its company is eligible.
- **Discovered link**: A same-domain URL associated with a company, retaining whether it came from automated discovery or company submission.
- **Eligibility event**: An auditable change in wallet eligibility and its resulting plan visibility or crawl/replay state.

### Success Criteria *(mandatory)*

#### Measurable Outcomes

- **SC-001**: 100% of extracted plans from companies below the charge requirement are absent from all end-user-facing plan responses.
- **SC-002**: 100% of a company's public plans are withdrawn after an insufficient-balance eligibility change is processed, while internal extracted records remain available to authorized operators.
- **SC-003**: No automated crawl or replay is started for an ineligible company after its eligibility change has been processed.
- **SC-004**: Replaying the same confirmed payment event/reference multiple times results in exactly one wallet credit.
- **SC-005**: A discovery refresh adds newly found eligible plan URLs and creates zero duplicate link records for URLs already stored for that site.
- **SC-006**: 100% of valid same-domain manual plan URLs can be submitted by an authorized company user and enter the existing review or extraction workflow.
- **SC-007**: 100% of authorized frontend and backend account/profile displays show the complete user's phone number; operational logs and telemetry do not contain full phone numbers.
- **SC-008**: An eligible published plan is consistently available across every applicable main, search, detail, and comparison surface, and unavailable across all of them after withdrawal.
- **SC-009**: No user email address is required for registration, authentication, or account/profile responses.
- **SC-010**: Pipeline models, tasks, services, and crawler/extraction/replay implementations are owned by `pipeline`; `admin_console` contains no pipeline implementation and communicates with it only through its declared interface.

## Assumptions

- The wallet and its ledger belong to this product. The payment library is used as a provider adapter for payment methods such as Zibal and other Iranian providers; confirmed provider payments credit the company wallet once.
- Charge eligibility is evaluated per company, not per user.
- The configured company wallet amount is a minimum balance threshold for eligibility. This specification does not introduce automatic per-plan debits or recurring charges; existing product metering rules, if any, remain separately defined.
- Public withdrawal is reversible: records are hidden from end users while ineligible and can become public again after eligibility is restored and publication quality checks still pass.
- Financial ineligibility blocks new discovery, capture, crawling, and replay; it does not delete stored traces, extracted plans, or provenance.
- The existing domain allowlist and URL normalization rules continue to apply to both automated and manually submitted links.
- Pipeline code is a separate bounded Django app named `pipeline`; the operator/admin console is a separate interface app and calls it through `pipeline.interfaces`.
- The supplied issue list ends with an empty "11-" item. **[NEEDS CLARIFICATION: Is there another bug or requirement for item 11?]**

## Out of Scope

- Replacing or reimplementing the payment library, payment gateway, or wallet ownership model.
- Changing plan extraction quality rules, plan schemas, or crawl ethics policy.
- Deleting historical traces or extracted plan records when public visibility is withdrawn.
- Adding email-based authentication or email contact requirements.
