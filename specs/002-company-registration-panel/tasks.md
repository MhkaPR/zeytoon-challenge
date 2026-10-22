---

description: "Task list for Company Registration & Company Panel"
---

# Tasks: Company Registration & Company Panel

**Input**: Design documents from `/specs/002-company-registration-panel/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/companies-api.md, quickstart.md

**Tests**: Included. The project constitution (Principle VIII) requires an automated test for
every domain behavior and a regression test for every bug fix, so test tasks are part of each
story.

**Organization**: Tasks are grouped by user story to enable independent implementation and
testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4, US5)
- All paths are relative to the repository root.

## Path Conventions

Web application: backend at `backend/src/`, frontend at `frontend/` (see plan.md). New backend
modules are created with `python manage.py startapp` (Principle XII).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the two new modules and wire configuration

- [ ] T001 Create the `companies` app with `python manage.py startapp companies` and register `companies` in `INSTALLED_APPS` in `backend/src/config/settings.py`
- [ ] T002 [P] Mount `path("api/v1/companies/", include("companies.urls"))` in `backend/src/config/urls.py` (create the placeholder `backend/src/companies/urls.py`); do NOT create a separate `panel` app — the panel surface belongs to `companies`
- [ ] T003 [P] Declare this feature's runtime constants in `CONSTANCE_CONFIG` in `backend/src/config/settings.py`: `COMPANY_STEP_DEFINITIONS`, `COMPANY_REQUIREMENT_MESSAGES`, `COMPANY_STEP_LOCKED_MESSAGE`, `COMPANY_EMPTY_STATE_MESSAGE` (defaults per data-model.md); do NOT add a duplicate-signal constant
- [ ] T004 [P] Create `backend/src/companies/tests/__init__.py` so pytest can discover the new test package

**Checkpoint**: Both modules exist, routing is mounted, and constants are declared.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared domain model, step resolution, owner scoping, and shared API error plumbing
that every user story depends on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 [P] Implement the `Company` model in `backend/src/companies/models.py` (inherits `utils.models.TimestampedModel`): `owner` (FK → `accounts.User`, non-null), `domain` (CharField, indexed), `company_name`, `representative_name`, `phone_number`, `internal_number` (blank allowed), `verification_status` (`pending`/`verified`/`rejected`), `charge_status` (`charged`/`not_charged`), `crawl_enabled` (default False), `is_archived` (default False), `archived_at` (null); current credit is NOT a stored field
- [ ] T006 [P] Implement the `VerificationDecision` model in `backend/src/companies/models.py`: `company` (FK), `outcome` (`approved`/`not_approved`), `actor` (FK → `accounts.User`), `decided_at`, `note` (blank); override `save()` to reject updates on existing rows and `delete()` to raise, so rows are insert-only (FR-016, FR-017)
- [ ] T007 [P] Implement the `CreditLedgerEntry` model in `backend/src/companies/models.py`: `company` (FK), `direction` (`charge`/`decharge`), `amount` (positive), `reason` (`payment`/`platform_view`/`adjustment`), `reference` (blank), `actor` (FK, null); override `save()`/`delete()` to make rows insert-only (FR-034, SC-013)
- [ ] T008 [P] Implement the `CompanyStepProgress` model in `backend/src/companies/models.py`: `company` (FK), `step_key`, `order`, `state` (`locked`/`open`/`saved`/`approved`/`rejected`), `last_saved_at` (null); add a uniqueness constraint on (`company`, `step_key`)
- [ ] T009 [P] Implement the `CompanyRegistrationDraft` model in `backend/src/companies/models.py`: `owner` (FK), `step_key`, `company` (FK, null), `payload` (JSONField), `expires_at`; drafts are not domain records
- [ ] T010 Add the step-sequence resolver and current-step logic in `backend/src/companies/selectors.py`: read `COMPANY_STEP_DEFINITIONS`, resolve each step's order, compute the ordered completion state, and return the current (first not-approved step whose predecessor is approved) — step one is `company_information`, next is `verification` with no owner input (FR-010, FR-011)
- [ ] T011 Add an owner-scoping helper in `backend/src/companies/selectors.py` that returns only companies the requesting user owns and raises a `not_found` `ApiError` for any other company (FR-028)
- [ ] T012 Create the migration for the companies models with `python manage.py makemigrations companies` and apply it with `python manage.py migrate`
- [ ] T013 [P] Define the `CompaniesInterface` in `backend/src/companies/interfaces.py` (the only sanctioned entry point for other modules, Principle V) exposing the reads/writes other modules need (company list, step progress, `can_manage_plans`, credit projection); the panel surface is internal to `companies` and does not need an interface entry
- [ ] T014 [P] Add the domain event logger helper (verification decisions, plan-prerequisite refusals, credit movements, ownership refusals, archival) in `backend/src/companies/events.py` reusing `utils.logging` masking so no phone number is logged unmasked (FR-046)
- [ ] T015 Register `Company`, `CompanyStepProgress`, `VerificationDecision`, and `CreditLedgerEntry` in `backend/src/companies/admin.py` for operator/admin-side reads (state + hooks only, no admin tooling UI) (FR-043, FR-044)

**Checkpoint**: Domain model, step resolution, scoping, interface, and logging exist; user
stories can begin.

---

## Phase 3: User Story 1 - Register a company (step one) and start verification (Priority: P1) 🎯 MVP

**Goal**: An authenticated user submits the standalone company-information form and gets a
pending, unverified company owned by them; step model and mid-step abandonment behave per spec.

**Independent Test**: Submit valid company info and confirm a pending unverified company exists
under the caller; submit invalid/missing fields and confirm rejection naming the field with no
company created; abandon a half-finished step and confirm only that step's input is cleared and
the user resumes at the same step.

### Tests for User Story 1 ⚠️

> Write these FIRST and confirm they FAIL before implementation.

- [ ] T016 [P] [US1] Contract test for `POST /api/v1/companies` and `GET /api/v1/companies` in `backend/src/companies/tests/test_registration.py` (201 created/pending, 400 invalid_field naming the offending field, no company on failure, internal_number optional, owner-scoped list) (FR-001..FR-006, SC-001)
- [ ] T017 [P] [US1] Step-locking test in `backend/src/companies/tests/test_step_locking.py`: a locked step is refused by direct address; step one precedes verification; verification needs no owner input (FR-008, FR-011)
- [ ] T018 [P] [US1] Mid-step abandonment test in `backend/src/companies/tests/test_mid_step_abandonment.py`: abandoning clears only that step's draft, keeps earlier saved steps intact, and resumes at the same step (FR-009, SC-005)

### Implementation for User Story 1

- [ ] T019 [P] [US1] Add Pydantic boundary schemas for the company-information payload (mandatory: `domain`, `company_name`, `representative_name`, `phone_number`; optional: `internal_number`) in `backend/src/companies/serializers.py` (FR-002, FR-003)
- [ ] T020 [US1] Implement `register_company()` in `backend/src/companies/services.py`: validate, create the `Company` (owner = caller, `verification_status=pending`), seed `CompanyStepProgress` for step one (`approved`/`saved`) and verification (`locked`), store the `domain` normalized (lowercased, scheme/path/`www` stripped — no duplicate detection, FR-041/FR-042)
- [ ] T021 [US1] Implement `save_step()` and `abandon_step()` in `backend/src/companies/services.py`: save persists the step (creating the company on step-one submit), abandon deletes only that (owner, step) draft and returns the same step (FR-009)
- [ ] T022 [US1] Implement `CompaniesView` (`POST` create) and `CompanyListView` (`GET` list, owner-scoped, each entry flagged `unverified` when pending/rejected) in `backend/src/companies/api.py` (FR-004, FR-005)
- [ ] T023 [US1] Implement `CompanyDetailView` (`GET` detail with `step_progress` and `current_step`) and `StepAbandonView` (`POST .../steps/{step_key}/abandon`) in `backend/src/companies/api.py`, enforcing step locking (FR-008, FR-010)
- [ ] T024 [US1] Wire the registration routes in `backend/src/companies/urls.py` (`""`, `"<int:pk>"`, `"<int:pk>/steps/<str:step_key>/abandon"`)
- [ ] T025 [US1] Emit structured logs for company creation and step abandon in `backend/src/companies/services.py` via `companies/events.py`, masking phone numbers (FR-046)

**Checkpoint**: User Story 1 works independently — a company can be registered and appears
pending/unverified.

---

## Phase 4: User Story 2 - Company panel entry, switching, and the continue-registration view (Priority: P2)

**Goal**: The panel shows an empty state with "Register new company" when the user owns none;
otherwise the user can switch companies, a verified one opens the full panel, and a pending or
rejected one opens the continue view (with a redirect when its full-panel URL is addressed
directly).

**Independent Test**: With verified/pending/rejected companies owned by one user, switching
selects each in turn; the verified one opens the full panel; each unverified one opens the
continue view listing completed/pending steps; a direct URL to an unverified company's panel
lands on the continue view.

### Tests for User Story 2 ⚠️

- [ ] T026 [P] [US2] Contract test for `GET /api/v1/companies/{id}/panel-entry`, `.../panel`, and `GET /api/v1/companies/panel-switcher` in `backend/src/companies/tests/test_panel_entry.py` (full_panel vs continue_registration, 303 redirect for unverified, empty state) (FR-023..FR-027, SC-003)
- [ ] T027 [P] [US2] Company-switching test in `backend/src/companies/tests/test_company_switching.py`: the payload reflects only the selected company; switching leaks no other company's verification/charge/credit/plan data (FR-022, FR-029)
- [ ] T028 [P] [US2] Owner-scoping test in `backend/src/companies/tests/test_owner_scoping.py`: every company/panel request for a company the caller does not own returns `404` and no data (FR-028, SC-006)

### Implementation for User Story 2

- [ ] T029 [US2] Implement `resolve_panel_entry()` and `switch_company()` in `backend/src/companies/services.py`: verified ⇒ `full_panel`; pending/rejected ⇒ `continue_registration` with step progress, current step, and verification status (FR-024, FR-025, FR-026)
- [ ] T030 [US2] Implement the panel views inside the `companies` module in `backend/src/companies/api.py`: `PanelEntryView` (entry), `PanelFullView` (full panel; `303` redirect to entry when unverified, never rendering the full panel), and `PanelSwitcherView` (switcher + empty-state payload) (FR-023, FR-027)
- [ ] T031 [US2] Wire the panel routes in `backend/src/companies/urls.py` (`"panel-switcher"`, `"<int:pk>/panel-entry"`, `"<int:pk>/panel"`)
- [ ] T032 [US2] Add the typed API client for panel + companies endpoints in `frontend/src/lib/api/companies.ts` (reusing the `frontend/src/lib/api/auth.ts` error/CSRF pattern)
- [ ] T033 [US2] Build the panel shell with the empty state ("Register new company") and company switcher in `frontend/app/panel/page.tsx` and `frontend/src/features/panel/CompanySwitcher.tsx` / `EmptyState.tsx` / `useActiveCompany.ts` (FR-022, FR-023)
- [ ] T034 [US2] Build the continue-registration view (completed/pending steps, route to the current step) in `frontend/src/features/company/ContinueRegistration.tsx` and `StepProgress.tsx`, and the route guard that renders it instead of the full panel in `frontend/app/panel/[companyId]/page.tsx` (FR-025, FR-026, FR-027)
- [ ] T035 [P] [US2] Add Persian/RTL copy for the panel, switcher, empty state, and continue view in `frontend/src/lib/i18n/strings.ts`
- [ ] T036 [P] [US2] Add frontend component tests for the switcher, empty state, and continue view in `frontend/tests/panel.test.tsx`

**Checkpoint**: User Stories 1 and 2 both work independently.

---

## Phase 5: User Story 3 - Verification outcome is decided, recorded, and logged (Priority: P3)

**Goal**: An operator records a decision off-feature; approved makes the company verified and
opens its panel, not-approved keeps it unverified and reopens step one, and every decision
appends exactly one immutable history entry.

**Independent Test**: Record an approval and confirm verified + reachable panel + one history
entry; record not-approved and confirm unverified + step one reopened + one history entry;
confirm an owner cannot set the status and earlier entries never change.

### Tests for User Story 3 ⚠️

- [ ] T037 [P] [US3] Contract test for `POST /api/v1/companies/{id}/verification-decisions` in `backend/src/companies/tests/test_verification_history.py` (201 approved ⇒ verified; 200 not-approved ⇒ rejected + step reopened; 403 for owner/non-operator; 422 invalid outcome) (FR-013..FR-019)
- [ ] T038 [P] [US3] Append-only immutability test in `backend/src/companies/tests/test_verification_history.py`: updates/deletes on `VerificationDecision` are rejected, a later decision leaves earlier entries unchanged, and both remain after a later approval (FR-016, FR-017, FR-020, SC-004)

### Implementation for User Story 3

- [ ] T039 [US3] Implement `record_verification_decision()` in `backend/src/companies/services.py`: create the immutable `VerificationDecision` and atomically update `Company.verification_status` — the only path allowed to change status (FR-019); on approval unlock the full panel; on not-approved reopen step one and set the verification step back to locked (FR-014, FR-015)
- [ ] T040 [US3] Implement `VerificationDecisionView` in `backend/src/companies/api.py` with an `admin`-role (django-guardian) permission, rejecting the company owner (FR-012)
- [ ] T041 [US3] Wire the decision route in `backend/src/companies/urls.py` (`"<int:pk>/verification-decisions"`)
- [ ] T042 [US3] Emit a structured verification-decision event (outcome, actor, masked identifiers) in `backend/src/companies/services.py` (FR-046)
- [ ] T043 [US3] Extend the continue view to communicate the current outcome (pending / not approved) without exposing the recorded reason in `frontend/src/features/company/ContinueRegistration.tsx` (FR-021)

**Checkpoint**: User Stories 1–3 work independently.

---

## Phase 6: User Story 4 - Plan prerequisites, credit, and crawl eligibility (Priority: P4)

**Goal**: Expose the plan-eligibility gate (verified + charged, naming every missing
prerequisite), model per-company credit as an append-only ledger whose projection is the
current credit, and allow crawl enabling only for charged accounts at no credit cost. Plans
themselves belong to another feature.

**Independent Test**: In a verified-but-uncharged company the gate reports blocked naming the
charge prerequisite; after charging it reports allowed; credit movements append exactly one
entry each and the projection equals the running total; uncharged crawl enabling is blocked,
and enabling crawl records no credit movement.

### Tests for User Story 4 ⚠️

- [ ] T044 [P] [US4] Contract test for `GET /api/v1/companies/{id}/plan-eligibility` in `backend/src/companies/tests/test_plan_eligibility.py` (allowed only when verified+charged; `missing` lists every unsatisfied prerequisite, both when both are absent; no plan is ever created) (FR-030, FR-031, SC-002)
- [ ] T045 [P] [US4] Credit-ledger test in `backend/src/companies/tests/test_credit_ledger.py`: exactly one append-only entry per charge/decharge, entries immutable on update/delete, `current_credit` equals the running total, and per-company isolation (FR-033, FR-034, SC-010, SC-013)
- [ ] T046 [P] [US4] Crawl-gating test in `backend/src/companies/tests/test_crawl_gating.py`: enabling crawl when uncharged is blocked naming `charged`; when charged it succeeds, changes no credit, and creates no ledger entry (FR-034a, FR-035)

### Implementation for User Story 4

- [ ] T047 [US4] Implement `can_manage_plans(company)` in `backend/src/companies/services.py` returning `{allowed, missing}` with every unsatisfied prerequisite (verified, charged) (FR-030, FR-031)
- [ ] T048 [US4] Implement `credit_projection(company)` in `backend/src/companies/selectors.py` (Σ charge − Σ decharge, computed per company) and expose it through `CompaniesInterface` (FR-034, SC-013)
- [ ] T049 [US4] Implement `record_credit_movement(company, direction, amount, reason, reference, actor)` in `backend/src/companies/services.py`: validate a positive amount and a known reason, append exactly one `CreditLedgerEntry`, and return the recomputed projection (FR-034)
- [ ] T050 [US4] Implement `set_crawl_enabled(company, enabled)` in `backend/src/companies/services.py`: require `charged`, toggle `crawl_enabled`, and record no credit movement (FR-035)
- [ ] T051 [US4] Implement `PlanEligibilityView`, `CompanyCreditView` (`GET` projection + entries), `CreditMovementView` (`POST`), and `CrawlView` (`POST`) in `backend/src/companies/api.py` (FR-030..FR-035)
- [ ] T052 [US4] Wire the routes in `backend/src/companies/urls.py` (`"<int:pk>/plan-eligibility"`, `"<int:pk>/credit"`, `"<int:pk>/credit/movements"`, `"<int:pk>/crawl"`)
- [ ] T053 [US4] Emit structured events for plan-prerequisite refusals and credit movements in `backend/src/companies/services.py` (FR-046)
- [ ] T054 [P] [US4] Add the plan-eligibility gate and credit summary to the full-panel shell in `frontend/src/features/panel/` and surface blocked actions with every missing prerequisite (FR-031)

**Checkpoint**: User Stories 1–4 work independently.

---

## Phase 7: User Story 5 - Ownership, archival, and abuse hooks (Priority: P5)

**Goal**: Ownership is single-owner and never changes in-product; deleting a user account
archives their companies (never hard-deletes); company state/hooks are readable by the
admin-side actor.

**Independent Test**: A user's in-product ownership-transfer attempt is refused; deleting an
owner's account leaves their companies archived and retrievable with nothing hard-deleted; the
abuse-related state is readable by an admin-side actor.

### Tests for User Story 5 ⚠️

- [ ] T055 [P] [US5] Ownership + archival test in `backend/src/companies/tests/test_archival_ownership.py`: in-product transfer refused; account deletion archives companies (`is_archived`, `archived_at`) and they remain retrievable; no hard-delete path exists; ownership is unchanged (FR-036..FR-040, SC-007, SC-008)
- [ ] T056 [P] [US5] Duplicate-handling boundary test in `backend/src/companies/tests/test_registration.py`: a repeated domain is accepted, the domain is stored normalized, and no signal model/endpoint/matching is produced (FR-041, FR-042, SC-009)

### Implementation for User Story 5

- [ ] T057 [US5] Implement `refuse_ownership_transfer()` in `backend/src/companies/services.py` returning a `409 ownership_transfer_unsupported` refusal that directs to the admin-coordinated manual process; ensure no in-product path mutates `Company.owner` (FR-036, FR-037)
- [ ] T058 [US5] Implement `archive_companies_for_user(user)` in `backend/src/companies/services.py` (sets `is_archived`/`archived_at`) and connect it to the `accounts` account-deletion signal via a `post_delete`/domain-event receiver in `backend/src/companies/apps.py` (FR-038, FR-039, FR-040)
- [ ] T059 [US5] Add the ownership-transfer refusal route/view (or a guarded `POST .../transfer-ownership`) in `backend/src/companies/api.py` and `backend/src/companies/urls.py`, and emit a structured refusal event (FR-037, FR-046)
- [ ] T060 [US5] Expose the abuse-related company state (verification, charge, credit projection, archival) read-only to the admin-side actor via `backend/src/companies/admin.py` and `CompaniesInterface` — no management tooling (FR-043, FR-044)

**Checkpoint**: All five user stories are independently functional.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Hardening and end-to-end validation

- [ ] T061 [P] Add a log-masking regression test covering registration, decisions, credit movements, and refusals in `backend/src/companies/tests/test_log_masking.py` (no unmasked phone number) (FR-046, SC-012)
- [ ] T062 [P] Verify runtime configurability: changing a constance constant (prerequisite message / step definition) takes effect without code changes, and document the operator path in `backend/src/companies/constants.py` docstring (FR-045, SC-011)
- [ ] T063 [P] Add OpenAPI annotations (drf-spectacular) to all new endpoints in `backend/src/companies/api.py` so `/api/schema/` matches `contracts/companies-api.md`
- [ ] T064 Run the full backend suite `pytest backend/src/companies/tests` and the frontend suite `yarn test` in `frontend/`, and fix any failures
- [ ] T065 Run the `quickstart.md` validation scenarios V1–V12 end-to-end and record results in `specs/002-company-registration-panel/quickstart.md`
- [ ] T066 Review against `.specify/memory/constitution.md` and `specs/002-company-registration-panel/plan.md`: confirm no cross-module table access (Principle V), no hard-coded tunables (Principle XIII), and no admin-frontend code was added

---

## Notes on coverage

- The plan-eligibility gate covers the spec's "listing" requirement (FR-030/FR-031) because a
  company publishes **plans**, whose entity and management UI belong to another feature; no
  plan model, migration, or plan-management endpoint is created here.
- No duplicate-signal model, constant, or endpoint is created; duplicate detection and
  resolution are the admin panel's responsibility (FR-042).
- The company's current credit is never a stored field — it is always the projection of
  `CreditLedgerEntry`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories.
- **User Stories (Phase 3–7)**: All depend on Foundational.
  - US1 is the MVP and can ship first.
  - US2 depends on US1's `Company`/step model existing (shared Foundational models).
  - US3, US4, US5 build on the `Company` model but are independently testable.
- **Polish (Phase 8)**: Depends on all desired stories.

### User Story Dependencies

- **US1 (P1)**: After Foundational — no other story dependencies.
- **US2 (P2)**: After Foundational; integrates with US1's company/step model.
- **US3 (P3)**: After Foundational; independently testable via the decision endpoint.
- **US4 (P4)**: After Foundational; independently testable via the gate/credit/crawl endpoints.
- **US5 (P5)**: After Foundational; independently testable via refusal/archival.

### Within Each User Story

- Tests first and failing → models → services → endpoints → frontend integration.

### Parallel Opportunities

- Setup: T002, T003, T004 in parallel after T001.
- Foundational: T005–T009 (models) in parallel; T013/T014/T015 in parallel.
- US1 tests T016–T018 in parallel.
- US2 tests T026–T028 in parallel; T035/T036 in parallel.
- US3 tests T037/T038 in parallel.
- US4 tests T044–T046 in parallel; T054 in parallel with backend work.
- US5 tests T055/T056 in parallel.
- Polish: T061, T062, T063 in parallel.

---

## Parallel Example: User Story 4

```bash
# Launch all tests for User Story 4 together:
Task: "Contract test for plan-eligibility in backend/src/companies/tests/test_plan_eligibility.py"
Task: "Credit-ledger test in backend/src/companies/tests/test_credit_ledger.py"
Task: "Crawl-gating test in backend/src/companies/tests/test_crawl_gating.py"

# Then parallel implementation work:
Task: "Implement can_manage_plans in backend/src/companies/services.py"
Task: "Implement credit_projection in backend/src/companies/selectors.py"
Task: "Add plan-eligibility gate to the full-panel shell in frontend/src/features/panel/"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (blocks all stories).
3. Complete Phase 3: User Story 1.
4. STOP and VALIDATE: run the US1 tests and quickstart V1, V5, V6.
5. Deploy/demo if ready.

### Incremental Delivery

1. Setup + Foundational → foundation ready.
2. US1 → test independently → MVP.
3. US2 → panel entry/switching/continue view.
4. US3 → verification decision + history.
5. US4 → plan gate + credit ledger + crawl.
6. US5 → ownership/archival/abuse hooks.
7. Polish → hardening and full quickstart validation.

### Parallel Team Strategy

After Foundational, split by story: Developer A on US1/US2 (registration + panel), Developer B
on US3 (verification), Developer C on US4 (credit/gate), Developer D on US5 (governance). Each
story touches distinct files and is independently testable.

---

## Notes

- [P] tasks touch different files and have no incomplete dependencies.
- Every domain behavior has an automated test (constitution Principle VIII).
- All tunable values are django-constance database constants or `settings.py` values — never
  hard-coded (Principle XIII).
- Company-scoped access is always owner-checked; non-owned companies return `404` (FR-028).
- All models inherit `TimestampedModel` from `backend/src/utils/models.py`.
- The admin/operator panel is a separate restricted-domain application; only state and hooks
  are modeled here.
