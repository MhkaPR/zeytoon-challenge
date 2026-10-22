# Phase 0 Research: Company Registration & Company Panel

All Technical Context unknowns are resolved below. Each entry records the decision, why it
was chosen, and what alternatives were considered. No `NEEDS CLARIFICATION` items remain.

## R1. Registration step model and step locking

- **Decision**: Model registration as a fixed, ordered set of steps resolved from a
  django-constance step definition (step one = company information, next step =
  verification). Persist per-company progress in a `CompanyStepProgress` row per step with an
  explicit `state` (`locked`, `open`, `saved`/`completed`, `approved`, `rejected`). The
  "current step" is the first non-approved step whose predecessor is approved; a step opens
  only when its predecessor is approved, so a locked step returns `403` on access by
  navigation or direct address.
- **Rationale**: The spec requires discrete, independently saved steps that stay locked until
  the previous step is approved (FR-007, FR-008, FR-010, FR-011) and is explicit that a
  unified wizard is wrong. A per-step progress row makes "which steps are done / which is
  current" a single indexed query and enforces locking server-side rather than only in the UI.
- **Alternatives considered**: A single wizard blob on `Company` (rejected: one interruption
  discards all data — the exact behavior the spec forbids); storing progress as a JSON field
  (rejected: locking/current-step logic becomes brittle and untestable, and constance step
  definitions could not be validated cleanly).

## R2. Company creation on submission vs. mid-step abandonment

- **Decision**: Create the `Company` record only when the company-information step is
  submitted and valid (FR-004). Persist in-progress form input for an *unsubmitted* step in a
  short-lived `CompanyRegistrationDraft` (keyed by owner + step) so that abandonment clears
  only **that** step's draft (FR-009) and previously saved steps are untouched; the user is
  returned to the same step.
- **Rationale**: The spec's assumption "no company record before step one is submitted" means
  mid-step abandonment for step one must still work without a company row, so a lightweight
  draft store is needed. Scoping the draft by (owner, step) makes "clear only this step"
  trivially correct and testable.
- **Alternatives considered**: Creating a draft company immediately (rejected: contradicts
  the spec's empty-state/no-record assumption); keeping drafts in client memory only
  (rejected: the spec requires server-side save/resume semantics and testable behavior).

## R3. Append-only verification history

- **Decision**: Store each decision as a `VerificationDecision` row; enforce immutability at
  the model layer by overriding `save()`/`delete()` to reject updates and deletes on existing
  rows, and restrict writes to the operator decision service/API only (FR-016, FR-017,
  FR-019). Status changes on `Company` happen exclusively inside the record-decision service.
- **Rationale**: SC-004 requires exactly one append-only entry per decision with no later
  modification or removal, and FR-019 forbids status changes through any other path. Model-
  level guards plus a single service entry point make the invariant hard to violate even from
  the admin.
- **Alternatives considered**: Free-text history field on `Company` (rejected: not
  append-only and loses actor/time structure); Django `LogEntry`/`simple_history`
  (considered for audit but rejected as insufficient for domain-specific outcome/actor/note
  and the immutable-append contract the spec demands).

## R4. Panel entry resolution and unverified redirect

- **Decision**: The panel is a user-facing surface over the company domain, so it lives inside
  the `companies` module — **no separate `panel` Django app**. A `companies` service resolves
  entry for the selected company: verified ⇒ full-panel payload; pending/rejected ⇒
  continue-registration payload (completed/current steps + route). The full-panel route is a
  server-guarded endpoint that returns a `303` redirect to the continue view when the company
  is unverified, so the full panel never renders with real data (FR-024, FR-025, FR-027).
- **Rationale**: SC-003 demands 100% of entries for unverified companies — including direct
  address — show the continue view and never the full panel; resolving the decision
  server-side keeps the rule in one place and immune to client routing gaps. Keeping the panel
  in `companies` avoids a Django app that would exist only to re-expose the same domain
  (Principle XII) and keeps all company-scoped logic behind one interface (Principle V).
- **Alternatives considered**: A separate `panel` Django app (rejected by the user: it would
  only re-expose `companies`); client-only route guards (rejected: a direct URL could briefly
  render the panel and the rule would not be authoritative); separate endpoints per state
  without a guard (rejected: leaks the full-panel shape for unverified companies).

## R5. Per-company charge status and credit ledger

- **Decision**: Store `charge_status` (`charged` / `not_charged`) on `Company` (not on `User`).
  Model credit as an append-only **`CreditLedgerEntry`** ledger — one immutable row per charge
  or decharge — and derive the company's current credit as the **projection** (running total)
  of its rows (FR-032, FR-033, FR-034, FR-034a). Charging/payment (funding the ledger) is out
  of scope; the metered platform-view decharge is owned by the views/search features, so this
  feature owns the ledger model, its projection, and the per-company accounting rule.
- **Rationale**: The spec requires a history of charging and decharging with the current credit
  as its projection, not a single mutable field — a ledger makes every movement auditable and
  makes the projection reproducible (SC-013). Company-scoping the ledger makes cross-company
  leakage structurally impossible (FR-033, SC-010).
- **Alternatives considered**: A single `credit` integer column on `Company` (rejected by the
  user: loses the movement history and cannot be audited/projected); a per-user credit model
  (rejected: explicitly contradicts per-company credit); a ledger owned by a separate
  `billing` module (deferred: this feature owns the company-scoped ledger it needs and exposes
  the write path other features call).

## R6. Plan eligibility gating and crawl eligibility

- **Decision**: Expose `companies.interfaces.can_manage_plans(company)`, returning
  `{ allowed, missing }` where `missing` lists **every** unsatisfied prerequisite (verified,
  charged); callers (the plan-owning feature) block the action and surface all missing
  prerequisites (FR-030, FR-031). The plan entity and its management UI are owned by another
  feature — no plan table or endpoint is created here. Enabling crawl is a `companies`
  operation requiring only a charged account; it costs nothing and records no credit movement
  (FR-035).
- **Rationale**: SC-002 requires blocks to name *every* missing prerequisite, so a set result
  is the only correct shape. Keeping the gate in `companies` and exposing it as a read
  interface preserves module boundaries (Principle V) and keeps the plan feature free to own
  the plan model.
- **Alternatives considered**: A `catalog`/plan module in this feature (rejected by the user:
  plans are another feature's concern); per-field boolean checks in the view (rejected: stops
  at the first failure); a single `can_manage` boolean (rejected: cannot report every missing
  prerequisite).

## R7. Duplicate-company detection (out of scope)

- **Decision**: Do not detect duplicates here. Store the company `domain` in normalized form
  (lowercased, scheme/path/`www` stripped) so the admin panel can use it; perform no matching,
  no signal, and no merge, and do not store a duplicate-signal model (FR-041, FR-042, SC-009).
- **Rationale**: The user assigned duplicate detection and resolution to the admin panel; a
  signal model or matching engine here would be dead weight and would drift from the admin's
  logic. Normalized storage is the only thing this feature needs to contribute.
- **Alternatives considered**: A `CompanyDuplicateSignal` model + warning response (rejected
  by the user: the admin panel's responsibility); an automatic uniqueness constraint on the
  domain (rejected: would auto-block registrations, which the spec forbids).

## R8. Ownership (single-owner, admin-only change) and archival

- **Decision**: `Company.owner` is a `ForeignKey` to `accounts.User`, non-null and unchanged
  by any in-product path. Any user-initiated ownership-transfer request returns a refusal that
  directs to the admin-coordinated manual process (FR-036, FR-037). Company account deletion
  archives companies via an `is_archived` flag (soft delete) triggered by the accounts deletion
  signal; nothing hard-deletes a company (FR-038, FR-039, FR-040, SC-007).
- **Rationale**: A single non-null owner FK structurally guarantees the single-owner model and
  that ownership never changes automatically; soft-delete flags preserve history, SEO, and
  complaints as required.
- **Alternatives considered**: A separate ownership-mapping table (rejected: overkill for a
  strict single-owner model); cascading hard delete (rejected by FR-039).

## R9. Runtime configuration (django-constance)

- **Decision**: All tunables live in django-constance with the database backend: step
  definitions/ordering, prerequisite messages, and step-lock messages (FR-045, SC-011). No
  custom settings model; values are read through `constance.config`. There is **no**
  duplicate-signal constant, because duplicate detection is the admin panel's responsibility
  (FR-042).
- **Rationale**: The constitution (Principle XIII) and FR-045 require runtime-adjustable
  tuning without code changes; constance already backs the project's runtime constants and
  provides an admin UI for operators (Principles XII, XIII).
- **Alternatives considered**: Values in `settings.py` only (rejected: not runtime-adjustable);
  a bespoke `CompanySettings` model (rejected: constance is the established, requested tool).

## R10. Observability and log masking

- **Decision**: Emit structured JSON events for verification decisions, plan-prerequisite
  refusals, credit movements, ownership-transfer refusals, and archival, reusing `utils.logging`
  (`SensitiveDataFilter`/`mask_text`) so no phone number appears unmasked (FR-046, SC-012).
  Use aggregation/sampling on the hot panel-entry path (anti-noise rule).
- **Rationale**: Principle VII and FR-046 require observable domain events with masking; the
  masking machinery already exists and must not be reimplemented (Principle XII).
- **Alternatives considered**: Ad-hoc `print`/per-request logging (rejected: violates
  structured-logging and anti-noise rules); a second masking implementation (rejected).

## R11. Frontend routing, switcher, and RTL/Persian copy

- **Decision**: Add `/panel` (empty state + switcher) and `/panel/[companyId]` (server-route
  guard: render full panel or continue view). Reuse the existing `src/lib/api` client pattern,
  `src/lib/i18n/strings.ts` for Persian copy, and the olive/RTL design system components
  (`Button`, `Card`, `Badge`, `StepProgress`). The switcher re-fetches per selected company so
  one company's state never leaks into another's view.
- **Rationale**: FR-022, FR-023, FR-029 and the design system's RTL/Persian requirement
  (DESIGN.md §8) demand scoped, localized UI; reusing existing components keeps the frontend
  consistent (Principle XII, codebase conventions).
- **Alternatives considered**: A single client-rendered panel route with query params
  (rejected: weakens the direct-URL redirect guarantee of FR-027); a second design language
  (rejected).
