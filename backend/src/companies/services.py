"""Domain services for company registration, verification, credit, and governance."""

from django.db import transaction
from django.utils import timezone

from accounts.exceptions import ApiError
from companies import constants, events, selectors
from companies.domain import normalize_domain
from companies.models import (
    Company,
    CompanyRegistrationDraft,
    CompanyStepProgress,
    CreditLedgerEntry,
    VerificationDecision,
)

MANDATORY_COMPANY_FIELDS = (
    "domain",
    "company_name",
    "representative_name",
    "phone_number",
)


# ---------------------------------------------------------------------------
# Registration (FR-001..FR-006)
# ---------------------------------------------------------------------------


def _seed_step_progress(company):
    """Create step rows: step one approved, every later step locked (FR-008)."""
    definitions = constants.step_definitions()
    for index, step in enumerate(definitions):
        if index == 0:
            state = CompanyStepProgress.State.APPROVED
        elif index == 1:
            state = CompanyStepProgress.State.OPEN
        else :
            state = CompanyStepProgress.State.LOCKED

        CompanyStepProgress.objects.create(
            company=company,
            step_key=step["key"],
            order=step["order"],
            state=state,
            last_saved_at=timezone.now(),
        )


def validate_company_fields(payload):
    """Validate the company-information payload, naming every offending field (FR-003)."""
    missing = [
        field
        for field in MANDATORY_COMPANY_FIELDS
        if not str(payload.get(field) or "").strip()
    ]
    if missing:
        raise ApiError(
            "invalid_field",
            "Some mandatory fields are missing or invalid.",
            fields={"fields": missing},
        )
    if not normalize_domain(payload.get("domain")):
        raise ApiError(
            "invalid_field",
            "The company domain is not valid.",
            fields={"fields": ["domain"]},
        )
    return missing


@transaction.atomic
def register_company(user, payload):
    """Create a company from the company-information step (FR-004).

    The domain is stored normalized for the admin panel's duplicate detection; this module
    performs no detection itself (FR-041, FR-042).
    """
    validate_company_fields(payload)
    company = Company.objects.create(
        owner=user,
        domain=payload["domain"],
        company_name=str(payload["company_name"]).strip(),
        representative_name=str(payload["representative_name"]).strip(),
        phone_number=str(payload["phone_number"]).strip(),
        internal_number=str(payload.get("internal_number") or "").strip(),
        verification_status=Company.VerificationStatus.PENDING,
    )
    _seed_step_progress(company)
    events.company_registered(company, actor=user)
    return company


@transaction.atomic
def save_step(user, company, step_key, payload):
    """Save one step's input independently (FR-007)."""
    from companies import steps as step_helpers

    step_helpers.assert_step_enterable(company, step_key)
    row = CompanyStepProgress.objects.select_for_update().get(
        company=company, step_key=step_key
    )
    row.state = CompanyStepProgress.State.SAVED
    row.last_saved_at = timezone.now()
    row.save(update_fields=["state", "last_saved_at", "updated_at"])
    CompanyRegistrationDraft.objects.create(
        owner=user, company=company, step_key=step_key, payload=payload or {}
    )
    return row


@transaction.atomic
def abandon_step(user, company, step_key):
    """Clear only this (owner, step) draft; earlier steps stay intact (FR-009, SC-005).

    The user resumes at the same step, never back at step one.
    """
    from companies import steps as step_helpers

    step_helpers.assert_step_enterable(company, step_key)
    CompanyRegistrationDraft.objects.filter(
        owner=user, company=company, step_key=step_key
    ).delete()
    row = CompanyStepProgress.objects.filter(
        company=company, step_key=step_key
    ).first()
    if row is not None and row.state == CompanyStepProgress.State.SAVED:
        row.state = CompanyStepProgress.State.OPEN
        row.save(update_fields=["state", "updated_at"])
    events.step_abandoned(company, step_key, actor=user)
    return step_key


# ---------------------------------------------------------------------------
# Verification (FR-012..FR-021) — operator-decided, UI out of scope
# ---------------------------------------------------------------------------


@transaction.atomic
def record_verification_decision(company, actor, outcome, note=""):
    """Record an append-only decision and update status — the only path allowed (FR-019)."""
    if outcome not in dict(VerificationDecision.Outcome.choices):
        raise ApiError("invalid_outcome", "Unknown verification outcome.")

    decision = VerificationDecision.objects.create(
        company=company,
        outcome=outcome,
        actor=actor,
        decided_at=timezone.now(),
        note=note or "",
    )

    if outcome == VerificationDecision.Outcome.APPROVED:
        company.verification_status = Company.VerificationStatus.VERIFIED
        company.save(update_fields=["verification_status", "updated_at"])
        # Approval completes registration: mark the verification step approved.
        CompanyStepProgress.objects.filter(
            company=company, step_key=constants.STEP_KEY_VERIFICATION
        ).update(state=CompanyStepProgress.State.APPROVED, updated_at=timezone.now())
    else:
        company.verification_status = Company.VerificationStatus.REJECTED
        company.save(update_fields=["verification_status", "updated_at"])
        # Not-approved reopens step one and re-locks verification (FR-015, FR-020).
        CompanyStepProgress.objects.filter(
            company=company, step_key=constants.STEP_KEY_COMPANY_INFORMATION
        ).update(state=CompanyStepProgress.State.OPEN, updated_at=timezone.now())
        CompanyStepProgress.objects.filter(
            company=company, step_key=constants.STEP_KEY_VERIFICATION
        ).update(state=CompanyStepProgress.State.LOCKED, updated_at=timezone.now())

    events.verification_decided(company, outcome, actor=actor)
    return decision


# ---------------------------------------------------------------------------
# Plan eligibility, credit, and crawl (FR-030..FR-035)
# ---------------------------------------------------------------------------


def can_manage_plans(company):
    """Return ``{allowed, missing}`` naming every unsatisfied prerequisite (FR-031)."""
    missing = []
    if not company.is_verified:
        missing.append("verified")
    if not company.is_charged:
        missing.append("charged")
    return {
        "allowed": not missing,
        "missing": missing,
        "message": constants.requirement_message(missing),
    }


@transaction.atomic
def record_credit_movement(company, direction, amount, reason, reference="", actor=None):
    """Append exactly one ledger entry and return the recomputed projection (FR-034)."""
    if direction not in dict(CreditLedgerEntry.Direction.choices):
        raise ApiError("invalid_movement", "Unknown credit direction.")
    if reason not in dict(CreditLedgerEntry.Reason.choices):
        raise ApiError("invalid_movement", "Unknown credit reason.")
    try:
        amount = int(amount)
    except (TypeError, ValueError):
        raise ApiError("invalid_movement", "The credit amount is not valid.")
    if amount <= 0:
        raise ApiError("invalid_movement", "The credit amount must be positive.")

    entry = CreditLedgerEntry.objects.create(
        company=company,
        direction=direction,
        amount=amount,
        reason=reason,
        reference=reference or "",
        actor=actor,
    )
    events.credit_movement_recorded(company, direction, amount, reason, actor=actor)
    return entry


def set_crawl_enabled(company, enabled):
    """Enable/disable crawl; requires a charged account and records no movement (FR-035)."""
    if enabled and not company.is_charged:
        raise ApiError(
            "company_requirement_missing",
            constants.requirement_message(["charged"]),
            http_status=409,
            fields={"missing": ["charged"]},
        )
    company.crawl_enabled = bool(enabled)
    company.save(update_fields=["crawl_enabled", "updated_at"])
    return company


# ---------------------------------------------------------------------------
# Ownership and archival (FR-036..FR-040)
# ---------------------------------------------------------------------------


def refuse_ownership_transfer(company, actor=None):
    """Refuse any in-product ownership transfer (FR-036, FR-037)."""
    events.ownership_transfer_refused(company, actor=actor)
    raise ApiError(
        "ownership_transfer_unsupported",
        "Ownership transfer is handled manually by the admin through a ticket.",
        http_status=409,
    )


def archive_companies_for_user(user):
    """Archive (never delete) a user's companies (FR-038, FR-039, FR-040)."""
    now = timezone.now()
    count = Company.objects.filter(owner=user, is_archived=False).update(
        is_archived=True, archived_at=now, updated_at=now
    )
    events.companies_archived(user, count)
    return count
