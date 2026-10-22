# Feature Specification: Company Registration & Company Panel

**Feature Branch**: `002-company-registration-panel`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "I want you to design the 'Company Registration' and 'Company Panel' sections for me. Where this fits: we're a hosting and server aggregator. Companies sign up to get a dedicated panel so they can manage their listings and credit. A user can have multiple companies, and for now company ownership is single-owner — each company has one owner. Company verification is manual and is done by an operator in the admin panel; the admin panel is not part of this work, but I want its effect on this section fully modeled, because from the user's point of view everything revolves around that verification. The company registration flow is multi-step and the steps are locked — a step doesn't open until the previous one is approved. Step one collects the company info: domain, company phone number, extension (optional), company name, and representative name. The rest is mandatory. When the user submits this form, a company is created for them with 'pending verification' status and appears in the user's company list with an 'unverified' flag. Step two is verification by the system/admin, whose UI is not ours, but from a state perspective it should have two outcomes: either it gets approved and the company becomes verified and its full panel opens, or it doesn't get approved — in the real world the operator calls and explains, and the result is recorded and logged in the system. I want this log and the 'rejection' path modeled in the spec, even if the call itself is manual. I also want a specific behavior for abandoning the form mid-way: if a user leaves a registration step half-finished, only that step's data is cleared and the user doesn't go back to step one; they continue from the same step. Data from previous steps stays intact. That means each step is a standalone form with its own separate save, not a unified wizard that loses everything on a single interruption. The second part is the company panel. When the user enters the company panel, they first need to be able to switch between their companies. If they have no companies, they see an empty state with a 'Register new company' button. If they do have companies, the panel behavior differs per company based on its verification status: a verified company goes into its full panel, but a pending or rejected company, instead of the full panel, sees a 'Continue company registration' view that shows them the current/next step and takes them there. This continue view must clearly show which step is done and which is pending, and must respect the step-locking rules. This means if the user goes directly via URL to the panel of an unverified company, they should be redirected to that continue view rather than having the full panel open. Now the business rules tied to this section. A listing can only be created and activated when the company is both verified and its account is charged. If either is missing, the action button must be blocked and tell the user exactly which prerequisite is missing. Enabling crawl is free but only possible for a charged account; crawl itself doesn't consume credit — only views that happen through the platform consume credit. For now consider credit per company, not per user. Duplicate-company prevention is the admin's job, so from us I only want a detection signal — e.g. domain uniqueness or a warning on a match — not a full dedup engine. A few other rules. Deleting a user account archives their companies and plans, i.e. soft delete; a company is never hard-deleted, because we need to keep history, SEO, and complaints. Company ownership transfer is manual and coordinated with the admin via a ticket; the ticket system itself is not part of this work, but I want it modeled that ownership is never changed automatically and is admin-controlled. Fraud and abuse management is also the admin's job; from us, just the states and hooks that this management needs are enough, not admin tools. On boundaries: the admin panel and operator interface, the ticket system, the crawl engine, the payment gateway and account charging, and search results and ranking design are all out of scope. From account charging I only need the 'charged / not charged' status, not the payment itself. From crawl, only this matters: 'enabling it requires a charged account and it doesn't consume credit itself.'"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Register a company (step one) and start verification (Priority: P1)

An authenticated user who owns no companies (or who wants an additional one) opens the "Register new company" flow. They fill in a single, standalone company-information form — company domain, company phone number, optional internal number, company name, and representative name — and submit it. On submission a company is created under their ownership with **pending verification** status, it appears in their company list flagged as **unverified**, and the next step (verification) becomes the company's current step while remaining locked until it is acted upon by the operator.

**Why this priority**: Nothing else in the feature exists without a company. This is the only path that creates one, and it is the entry point for the whole verification-centered experience.

**Independent Test**: From a user with no companies, submit a valid company-information form and confirm a company is created, owned by that user, listed as unverified with pending status, and that no part of the full panel is reachable for it yet.

**Acceptance Scenarios**:

1. **Given** a logged-in user with no companies, **When** they submit the company-information form with domain, company phone number, company name, and representative name filled in, **Then** a company is created for them with pending-verification status and appears in their company list with an unverified flag.
2. **Given** the company-information form, **When** the user submits it with the internal-number field left empty, **Then** the submission is accepted (the internal number is optional, and is the company's internal line — the extension dialled after the company phone number).
3. **Given** the company-information form, **When** the user submits it with any mandatory field missing or invalid, **Then** the submission is rejected with a message naming the offending field, and no company is created.
4. **Given** a newly created pending company, **When** the user opens its panel, **Then** they are sent to the "Continue company registration" view rather than a full panel, and the verification step is shown as locked pending the operator's decision.
5. **Given** a user who already owns one or more companies, **When** they register another company, **Then** a second company is created under the same owner and both appear in their company list.

---

### User Story 2 - Company panel entry, switching, and the continue-registration view (Priority: P2)

A logged-in user enters the company panel. If they own no companies they see an empty state with a "Register new company" button. If they own companies, they can switch between them, and the panel adapts to the selected company's verification status: a verified company opens its full panel, while a pending or rejected company opens a "Continue company registration" view that shows which steps are complete and which is pending, and takes them to the current step. Reaching an unverified company's panel directly by URL redirects to that same continue view instead of opening the full panel.

**Why this priority**: This is the container every company interaction lives in, and it is where the "everything revolves around verification" promise becomes visible to the user. It is lower than registration only because it has nothing to show until a company exists.

**Independent Test**: With three companies in the states verified / pending / rejected owned by one user, confirm: switching selects each in turn; the verified one opens the full panel; each unverified one opens the continue view listing completed and pending steps; and a direct URL to an unverified company's panel lands on the continue view.

**Acceptance Scenarios**:

1. **Given** a user who owns no companies, **When** they open the company panel, **Then** they see an empty state containing a "Register new company" button.
2. **Given** a user who owns more than one company, **When** they open the company panel, **Then** they can switch the active company and the panel content follows the selected company.
3. **Given** the selected company is verified, **When** the user opens its panel, **Then** the full company panel is shown.
4. **Given** the selected company is pending verification, **When** the user opens its panel, **Then** the "Continue company registration" view is shown, the completed steps are marked done, the verification step is marked pending, and the user is offered the route to the current step.
5. **Given** the selected company was rejected, **When** the user opens its panel, **Then** the "Continue company registration" view is shown with the registration step marked as the current step to act on.
6. **Given** an unverified company owned by the user, **When** the user navigates directly to that company's full-panel URL, **Then** they are redirected to the continue-registration view for that company, and the full panel is not rendered.
7. **Given** a user switches from a verified company to a pending one, **When** the switch completes, **Then** the pending company's continue view is shown and no full-panel data for the pending company is exposed.

---

### User Story 3 - Verification outcome is decided, recorded, and logged (Priority: P3)

An operator — working in an interface that is not part of this feature — reviews a pending company and records a decision. The two outcomes are **approved**, which makes the company verified and opens its full panel, and **not approved**, which keeps the company unverified and reopens the registration step for correction. In both cases the decision is written to an append-only verification history: who decided, when, which outcome, and the recorded reason or note that the operator used when calling the company. The company owner is never able to set or influence the outcome.

**Why this priority**: The verification decision is the pivot of the entire section, and the log is a business record the operator's call depends on. It is P3 only because it is produced by an actor outside this feature's UI, so this feature contributes the state model, the record, and the hooks rather than the screen.

**Independent Test**: Change a pending company's status through the recorded verification-decision path to approved and confirm the company becomes verified, its full panel opens, and a history entry exists; then repeat with a not-approved outcome and confirm the company stays unverified, its registration step reopens, and a history entry exists.

**Acceptance Scenarios**:

1. **Given** a pending company, **When** the verifying actor records an approval, **Then** the company becomes verified, its full panel becomes reachable, and an append-only history entry records the outcome, the actor, the time, and any note.
2. **Given** a pending company, **When** the verifying actor records a not-approved outcome, **Then** the company remains unverified, its registration step reopens as the current step, and an append-only history entry records the outcome, the actor, the time, and any note.
3. **Given** a company with verification history, **When** a new decision is recorded, **Then** the earlier entries remain readable and unchanged (the history is append-only).
4. **Given** a company owner, **When** they attempt to set or change their own company's verification status, **Then** the attempt is refused because only the verifying actor can decide.
5. **Given** a company was approved, **When** its verification status is examined later, **Then** the approval and any subsequent decisions are both traceable in the history.

---

### User Story 4 - Plan prerequisites, credit, and crawl eligibility (Priority: P4)

Inside a verified company's panel, the user tries to create or activate a **plan** (a host, server, or similar offering the company publishes). The action is blocked unless the company is both verified and its account is charged, and when it is blocked the user is told exactly which prerequisite is missing. What a company publishes is a **plan**, not a generic listing; the plan entity and its management UI are owned by another feature and are out of scope here — this feature owns only the **eligibility gate** that decides whether plan actions are allowed. Credit is a per-company ledger: each charge or decharge is recorded, and the company's current credit is the projection of that ledger. Enabling crawling is free but requires a charged account, and crawling itself never consumes credit — only views that occur through the platform consume credit.

**Why this priority**: These are the commercial rules that make a company's panel valuable, and they depend on the verification and panel work already existing. They are P4 because the panel must open before these controls are reachable.

**Independent Test**: In a verified company that is not charged, evaluate a plan action and confirm the gate reports it blocked naming the missing charge prerequisite; charge the company and confirm the gate reports the action allowed; then disable charging again and confirm enabling crawl is likewise blocked while crawl itself does not reduce credit.

**Acceptance Scenarios**:

1. **Given** a verified company whose account is not charged, **When** a plan action is evaluated, **Then** the gate reports it blocked and the message says the account is not charged.
2. **Given** an unverified company, **When** a plan action is evaluated, **Then** the gate reports it blocked and the message says the company is not yet verified.
3. **Given** a company that is neither verified nor charged, **When** a plan action is evaluated, **Then** the blocked message names both missing prerequisites.
4. **Given** a verified and charged company, **When** a plan action is evaluated, **Then** the gate reports it allowed (the plan entity and its management UI are out of scope).
5. **Given** a charged company, **When** the user enables crawling, **Then** crawling is enabled without consuming credit.
6. **Given** a company whose account is not charged, **When** the user tries to enable crawling, **Then** the action is blocked because a charged account is required.
7. **Given** a company with crawling enabled, **When** traffic is served through the crawl path, **Then** the company's credit is unchanged (only views through the platform consume credit).
8. **Given** two companies owned by the same user, **When** one company's charge or credit changes, **Then** the other company's charge and credit are unaffected (credit is per company).
9. **Given** a company, **When** credit is charged or decharged, **Then** exactly one ledger entry is recorded for the movement and the company's current credit is the projection of all its ledger entries.

---

### User Story 5 - Ownership, archival, and abuse hooks (Priority: P5)

The governance behaviors around a company are modeled but not automated: ownership is single-owner and only ever changed by an admin-coordinated manual process, deleting a user account archives their companies instead of removing them, and the company exposes the states and hooks that admin-side fraud and abuse management needs. Duplicate-company detection and resolution are the admin panel's responsibility and are out of scope for this feature; this feature only stores the company domain in a normalized form that the admin panel can use.

**Why this priority**: These are durability, trust, and compliance guarantees. They do not gate the day-one flows above, so they come last, but they must be modeled now because retrofitting history and ownership rules later is far more costly.

**Independent Test**: Confirm a user cannot transfer ownership themselves; mark a user account deleted and confirm their companies remain resolvable in an archived state and are never hard-deleted; and confirm the abuse-related states are readable by an admin-side actor.

**Acceptance Scenarios**:

1. **Given** a company with an owner, **When** the owner tries to hand the company to another user from inside the panel, **Then** the transfer is refused and the user is directed to the admin-coordinated manual process.
2. **Given** a company whose ownership was transferred through the admin-coordinated process, **When** the company is examined, **Then** it shows exactly one owner (single-owner model) and the change is traceable.
3. **Given** a user account that is deleted, **When** the deletion is processed, **Then** that user's companies are archived rather than removed, and they remain available to history, search-engine, and complaint handling.
4. **Given** an archived company, **When** its history is requested, **Then** it is still retrievable, and no operation hard-deletes a company.
5. **Given** a company suspected of fraud or abuse, **When** an admin-side actor needs to act, **Then** the company's state and the required hooks are available to that actor without this feature providing admin tooling.

---

### Edge Cases

- **Step abandoned mid-way**: a user who leaves a registration step half-finished has *only that step's* unsaved input cleared; they are not returned to the first step, they resume at the same step, and any data from previously completed and saved steps remains intact.
- **Step locking**: a step that follows an unapproved step is never enterable — by navigation, by direct address, or by reaching the panel directly.
- **Direct address to an unverified company's full panel**: resolved by redirect to the continue-registration view; the full panel must not render even briefly with real data.
- **Accessing another user's company**: a user requesting a company they do not own sees no company data (treated as not found or not permitted); company scope is enforced on every company-scoped request.
- **Company with a domain that matches an existing company**: detection and resolution belong to the admin panel; this feature stores the normalized domain and does not auto-reject, auto-merge, or surface a duplicate signal of its own.
- **Rejected company accessed again**: the continue view presents the registration step as the current step; the earlier rejection remains in the append-only history.
- **Approval after an earlier rejection**: the company becomes verified, the full panel opens, and both the rejection and the approval remain in the history.
- **Plan action blocked with both prerequisites missing**: the message names both, rather than stopping at the first failure.
- **Charge removed after plans exist**: existing plans are not silently destroyed; whether they remain active is governed by the charged/verified prerequisite rules and must be reported to the user when they attempt plan actions.
- **Crawl enabled then account becomes uncharged**: crawl use consumes no credit, so the account's credit is unchanged; the charged requirement remains a precondition the user is told about when enabling.
- **Credit movement with no prior entries**: the company's current credit is zero; the first charge or decharge creates the first ledger entry and the projection reflects it.
- **Credit projection audit**: reconstructing the company's current credit from its ledger entries always equals the projected value, and no ledger entry is altered or removed.
- **Deleted user who was the sole owner of a company**: the company is archived, is never hard-deleted, and ownership is not transferred automatically.
- **Company in an abuse-related state**: the state is visible to the admin-side actor and blocks or explains the user-facing actions that depend on it, without this feature exposing management tooling.
- **User with several companies in mixed states**: the panel reflects the selected company's state only; switching companies never leaks one company's verification, credit, or plan data into another.

## Requirements *(mandatory)*

### Functional Requirements

**Company registration (step one)**

- **FR-001**: The system MUST allow an authenticated user to start registering a new company, and MUST create a distinct company record per registration.
- **FR-002**: The company-information step MUST collect: company domain, company phone number, company name, and representative name, plus an optional internal number (the extension dialled after the company phone number); every field except the internal number MUST be mandatory.
- **FR-003**: The system MUST reject a company-information submission that misses or fails to validate any mandatory field, MUST name the offending field in the message, and MUST NOT create a company in that case.
- **FR-004**: On a successful company-information submission, the system MUST create the company under the submitting user's ownership with a pending-verification status.
- **FR-005**: A company in pending-verification status MUST appear in the owner's company list flagged as unverified.
- **FR-006**: A user MUST be able to own and manage multiple companies, and every company created by a user MUST be owned by exactly one owner (single-owner model).

**Step model and mid-step abandonment**

- **FR-007**: Company registration MUST be modeled as discrete, independently saved steps, where each step is a standalone form with its own save, rather than one unified wizard whose single interruption discards all entered data.
- **FR-008**: Each step MUST remain locked until the preceding step is approved; a locked step MUST NOT be enterable by navigation or by direct address.
- **FR-009**: When a user leaves a step half-finished, the system MUST clear only that step's unsaved input, MUST keep data saved by previously completed steps intact, and MUST return the user to the same step rather than to the first step.
- **FR-010**: The system MUST expose, for any company, which steps are completed and which step is the current (next) step.
- **FR-011**: The registration steps MUST be resolvable to a step sequence whose first step is the company-information step and whose next step is verification; the verification step MUST NOT require input from the company owner.

**Verification (operator-decided, UI out of scope)**

- **FR-012**: Company verification MUST be performed by an operator actor outside this feature's user interface; the company owner MUST NOT be able to set, change, or influence their own verification outcome.
- **FR-013**: Verification MUST have exactly two outcomes: approved, making the company verified, and not approved, leaving the company unverified.
- **FR-014**: On approval, the company MUST become verified and its full company panel MUST become reachable.
- **FR-015**: On a not-approved outcome, the company MUST remain unverified and its company-information step MUST reopen as the current step so the owner can correct and resubmit it.
- **FR-016**: Every verification decision MUST be recorded in an append-only verification history containing at least the outcome, the deciding actor, the decision time, and the recorded reason or note.
- **FR-017**: Verification history entries MUST remain readable and MUST NOT be altered or removed by later decisions.
- **FR-018**: The system MUST record the operator's decision so that the outcome a company owner sees and the recorded history agree, even though the explanatory call itself is manual and outside the system.
- **FR-019**: The system MUST NOT permit verification status to change through any path other than a recorded verification decision.
- **FR-020**: A not-approved outcome MUST NOT be terminal: it MUST reopen the company-information step so the owner can correct and resubmit, and resubmission MUST return the company to pending verification. Repeated not-approved outcomes MUST be allowed, and the earlier rejections MUST remain in the history after any later approval.
- **FR-021**: The continue-registration view MUST communicate the company's current verification outcome to the owner (pending or not approved). The recorded reason or note is retained as the operator's audit record and is conveyed to the owner through the operator's call rather than being displayed in the continue view.

**Company panel, switching, and routing**

- **FR-022**: The company panel MUST let a user switch between the companies they own, and all panel content MUST reflect the currently selected company.
- **FR-023**: When a user owns no companies, the company panel MUST show an empty state containing a "Register new company" button.
- **FR-024**: For a verified company, entering the company panel MUST open the full company panel.
- **FR-025**: For a pending or rejected company, entering the company panel MUST show a "Continue company registration" view instead of the full panel.
- **FR-026**: The continue-registration view MUST show which steps are completed and which step is pending, MUST respect step locking, and MUST take the user to the current step.
- **FR-027**: When a user addresses an unverified company's full-panel location directly, the system MUST redirect them to that company's continue-registration view and MUST NOT render the full panel.
- **FR-028**: Company-scoped requests MUST be limited to companies the requesting user owns; a user MUST NOT see another user's company data.
- **FR-029**: Switching companies MUST NOT expose one company's verification status, charge status, credit, or plans while another company is selected.

**Plan prerequisites, credit, and crawl**

- **FR-030**: The system MUST expose an eligibility gate such that a plan action (creating or activating a plan) is allowed only when the company is both verified and its account is charged. The plan entity and its management UI are owned by another feature and are out of scope here.
- **FR-031**: When a plan action is evaluated as blocked, the system MUST report the action as blocked and state exactly which prerequisite is missing; when both are missing, both MUST be named.
- **FR-032**: The system MUST model the charge status of a company as charged or not charged, and MUST NOT implement the charging or payment process itself.
- **FR-033**: Credit MUST be accounted per company, not per user; a change to one company's credit or charge status MUST NOT affect the user's other companies.
- **FR-034**: Credit MUST be modeled as an append-only ledger of charge and decharge movements, one entry per movement, and the company's current credit MUST be the projection (running total) of its ledger entries; no ledger entry may be altered or removed.
- **FR-034a**: Only views that occur through the platform MUST consume credit — that is, a decharge is recorded for each metered platform view; enabling crawl and crawl traffic MUST NOT record any credit movement.
- **FR-035**: Enabling crawling MUST require a charged account, MUST be free of charge, and MUST NOT itself consume credit.

**Ownership, archival, and governance hooks**

- **FR-036**: Company ownership MUST be single-owner at all times and MUST never change automatically.
- **FR-037**: Ownership transfer MUST be performed only through an admin-coordinated, manual process initiated by a ticket outside this feature; the system MUST refuse in-product attempts by a user to transfer ownership and MUST direct them to that manual process.
- **FR-038**: Deleting a user account MUST archive that user's companies (soft delete) rather than removing them.
- **FR-039**: A company MUST never be hard-deleted, so that history, search-engine visibility, and complaint handling are preserved.
- **FR-040**: Archived companies MUST remain retrievable for history and complaint handling.
- **FR-041**: Company domains MUST be stored in a normalized form suitable for duplicate detection by the admin panel, and this feature MUST NOT block or merge registrations automatically on the basis of a domain match.
- **FR-042**: Duplicate-company detection and resolution MUST remain the admin panel's responsibility; this feature MUST NOT implement a detection signal or a deduplication engine, and MUST NOT depend on one.
- **FR-043**: The system MUST expose the company states and hooks that admin-side fraud and abuse management requires, without providing admin management tooling.
- **FR-044**: This feature MUST NOT implement or depend on the admin panel or operator interface, the ticket system, the crawl engine, the payment gateway or account charging, or search-result ranking design.

**Configuration and observability**

- **FR-045**: Every tunable value in this feature (step definitions, prerequisite messages, and similar) MUST be configurable by operators at runtime rather than hard-coded in application code.
- **FR-046**: The system MUST record verification decisions, plan-prerequisite refusals, credit movements, and ownership changes as structured, observable events, and MUST mask or omit personal data such as phone numbers from logs.
- **FR-047**: The feature MUST prefer established, maintained libraries and framework-provided generators over hand-written implementations for any capability that already has a well-supported library.

### Key Entities *(include if feature involves data)*

- **Company**: The registrable business entity owned by exactly one user. Holds the company domain, company phone number, optional internal number (the extension dialled after the company phone number), company name, representative name, a verification status, step progress, a charge status, and an archival (soft-deleted) state. Never hard-deleted.
- **Company Owner**: The single user linked to a company. Ownership is single-owner, and any change is admin-coordinated and manual, never automatic.
- **Registration Step**: A discrete, independently saved stage of company registration with its own form, save, and completion state, plus a locked/open state driven by whether the preceding step was approved. Step one is company information; the following step is verification.
- **Verification Decision / History Entry**: An append-only record of one verification outcome for a company, capturing the outcome (approved or not approved), the deciding actor, the decision time, and the recorded reason or note. Entries are never altered or deleted.
- **Company Charge Status**: A per-company charged / not-charged indicator. Only the status is modeled; the charging process itself is out of scope.
- **Credit Ledger Entry**: One append-only, immutable record of a credit movement for a company — a charge (credit added) or a decharge (credit consumed), with the direction, amount, reason, and time. Never altered or removed.
- **Company Credit (projection)**: The company's current credit, computed as the running total (projection) of its credit ledger entries. Accounting is per company, never per user. Enabling crawl does not reduce it; only metered platform views add decharges.
- **Plan Eligibility Gate**: The rule that a plan action (creating or activating a plan) is allowed only when the company is verified and charged, returning every missing prerequisite. The plan entity and its management UI belong to another feature and are out of scope here.
- **Crawl Setting**: A per-company switch that enables crawling. It requires a charged account, costs nothing, and consumes no credit.
- **Abuse State / Hook**: The condition and data points exposed for admin-side fraud and abuse management without admin tooling.
- **Feature Settings**: The operator-configurable tunables for this feature — step definitions and prerequisite messages — held outside application code.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user with no companies can go from opening the company panel to having a pending company listed as unverified in under 3 minutes.
- **SC-002**: 100% of plan actions evaluated without both prerequisites satisfied are reported blocked, and 100% of those blocks name every missing prerequisite.
- **SC-003**: 100% of company-panel entries for unverified companies — including entries by direct address — show the continue-registration view and never the full panel.
- **SC-004**: 100% of decided verifications produce exactly one append-only history entry recording the outcome, the deciding actor, the time, and the recorded note, and no existing entry is ever modified or removed.
- **SC-005**: A user who abandons a step half-finished loses only that step's unsaved input and resumes at the same step in 100% of tested interruptions; no data saved by an earlier completed step is lost.
- **SC-006**: 0% of company-scoped requests return data for a company the requester does not own.
- **SC-007**: 100% of deleted user accounts leave their companies archived and retrievable, and 0 companies are hard-deleted across the tested lifecycle.
- **SC-008**: 100% of in-product ownership-transfer attempts by users are refused and directed to the admin-coordinated manual process; 0 ownership changes occur automatically.
- **SC-009**: 100% of company domains are stored in a normalized form, and 0 registrations are silently blocked or merged by this feature on the basis of a domain match.
- **SC-010**: Changing one company's charge status or credit never changes another company's charge status or credit in any tested scenario.
- **SC-011**: 100% of the tunable values in this feature can be changed by operators at runtime without editing application code.
- **SC-012**: No log entry produced by this feature contains an unmasked phone number.
- **SC-013**: For every company, the current credit always equals the running total of its ledger entries, and 100% of charge/decharge movements produce exactly one append-only ledger entry that is never altered or removed.

## Assumptions

- **Verification is two steps, not more**: registration ends once verification is approved — there is no further user-input step before the full panel opens. Additional profile setup beyond the listed company fields is out of scope.
- **No company record before step one is submitted**: since the company is created on submission, a user with an unfinished, unsubmitted company-information form owns no company yet and therefore sees the empty state; the mid-step abandonment rule clears that unsubmitted input and leaves them on the same step.
- **Rejection reopens the company-information step**: a not-approved outcome returns the owner to step one for correction, with the rejection preserved in history, and resubmission returns the company to pending verification. A company may be rejected and resubmitted repeatedly with no cooldown.
- **Rejection reason is recorded internally**: the operator's explanatory call is manual and outside the system; whatever is written into the decision record is retained as the audit reason and is not shown in the continue view.
- **Crawl inherits the verification requirement** from panel access: crawling is reachable only from a verified company's full panel, and additionally requires a charged account. It costs nothing and consumes no credit.
- **"Charged" is an externally set per-company status**: charging is performed by the payment process, which is out of scope; this feature reads the status and enforces its consequences.
- **Credit is a per-company ledger projected to a current balance**: the ledger records charges and decharges as append-only entries; the running total is the company's current credit. Views through the platform are the only decharge source; the exact metering of platform views is defined by the views/search features and is out of scope here, as is funding the ledger (payment/charging).
- **A user may own any number of companies** with no per-user cap in this feature; each is independently verified, charged, and credited.
- **The admin panel, operator interface, ticket system, crawl engine, payment/charging implementation, plan (host/server offering) management, duplicate-company detection, and search ranking are delivered elsewhere**; this feature models their effects, states, and hooks only.
- **Roles and authentication are provided by the existing login feature**: this feature assumes an authenticated user and an admin/operator actor, and does not re-specify authentication.
- **Company domain is the practical duplicate-detection key for the admin panel**, since it is the most reliable public identifier; this feature stores it normalized and leaves detection, matching heuristics, and resolution entirely to the admin panel.
- **Archived companies remain resolvable for history, SEO, and complaints**, and any operator-configurable retention behavior follows the project's data-retention principle.
