"""Read-side helpers: owner scoping, step resolution, and the credit projection."""

from django.db.models import Sum

from companies import constants
from companies.models import Company, CompanyStepProgress


def owned_company_or_error(user, company_id):
    """Return the company when ``user`` owns it, else raise a ``not_found`` ``ApiError``.

    Every company-scoped request is limited to the requester's own companies (FR-028); a
    company the caller does not own is reported as not found so no data leaks (SC-006).
    """
    from accounts.exceptions import ApiError

    company = Company.objects.filter(pk=company_id, owner=user).first()
    if company is None:
        raise ApiError("not_found", "Company not found.", http_status=404)
    return company


def list_owned_companies(user):
    """Return the caller's companies, newest first, with archived ones included."""
    return Company.objects.filter(owner=user)


def step_progress(company):
    """Return the company's step rows ordered by configured step order."""
    rows = {row.step_key: row for row in company.step_progress.all()}
    return [rows[key] for key in constants.step_keys() if key in rows]


def step_progress_payload(company):
    """Serialize step progress for the API (FR-010, FR-026)."""
    return [
        {
            "step_key": row.step_key,
            "order": row.order,
            "state": row.state,
            "completed": row.state
            in {
                CompanyStepProgress.State.APPROVED,
                CompanyStepProgress.State.SAVED,
            },
        }
        for row in step_progress(company)
    ]


def current_step(company):
    """Return the current (next) step key, or ``None`` when registration is complete.

    The current step is the first configured step whose predecessor is approved and which is
    not itself approved (FR-010, FR-011).
    """
    rows = {row.step_key: row for row in company.step_progress.all()}
    previous_approved = True
    for step in constants.step_definitions():
        key = step["key"]
        row = rows.get(key)
        if not previous_approved:
            return None
        if row is None or row.state != CompanyStepProgress.State.APPROVED:
            return key
        previous_approved = True
    return None


def credit_projection(company):
    """Return the company's current credit as the projection of its ledger (FR-034).

    ``Σ charge − Σ decharge`` computed for this company only (FR-033). The ledger is the
    source of truth; nothing is cached here, so the value always equals the running total
    (SC-013).
    """
    from companies.models import CreditLedgerEntry

    charges = (
        company.credit_entries.filter(direction=CreditLedgerEntry.Direction.CHARGE)
        .aggregate(total=Sum("amount"))
        .get("total")
        or 0
    )
    decharges = (
        company.credit_entries.filter(direction=CreditLedgerEntry.Direction.DECHARGE)
        .aggregate(total=Sum("amount"))
        .get("total")
        or 0
    )
    return int(charges) - int(decharges)


def credit_entries_payload(company):
    """Serialize the credit ledger, newest first (FR-034)."""
    return [
        {
            "id": entry.pk,
            "direction": entry.direction,
            "amount": entry.amount,
            "reason": entry.reason,
            "reference": entry.reference,
            "created_at": entry.created_at.isoformat(),
        }
        for entry in company.credit_entries.all()
    ]


def companies_awaiting_verification():
    """Return non-archived companies still awaiting a verification decision (FR-001)."""
    return Company.objects.filter(
        is_archived=False,
        verification_status=Company.VerificationStatus.PENDING,
    ).order_by("created_at")


def duplicate_domain_ids(company):
    """Return ids of other companies sharing this normalized domain (FR-004).

    Advisory only — the caller never auto-rejects or auto-merges on a match.
    """
    if not company.domain:
        return []
    from companies.domain import canonical_domain

    target = canonical_domain(company.domain)
    return list(
        pk
        for pk, domain in Company.objects.exclude(pk=company.pk).values_list(
            "pk", "domain"
        )
        if canonical_domain(domain) == target
    )


def company_or_error(company_id):
    """Return a company by id or raise a ``not_found`` ``ApiError``."""
    from accounts.exceptions import ApiError

    company = Company.objects.filter(pk=company_id).first()
    if company is None:
        raise ApiError("not_found", "Company not found.", http_status=404)
    return company


def pending_approval_payload(company):
    """Serialize one approval-queue row with the duplicate-domain warning (FR-001, FR-004)."""
    from utils.logging import mask_phone

    duplicates = duplicate_domain_ids(company)
    return {
        "company_id": company.pk,
        "company_name": company.company_name,
        "representative_name": company.representative_name,
        "domain": company.domain,
        "phone_masked": mask_phone(company.phone_number),
        "registered_at": company.created_at.isoformat(),
        "duplicate_domain_warning": bool(duplicates),
        "duplicate_of": duplicates,
    }
