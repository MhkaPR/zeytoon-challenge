"""Operator-facing approval and verification services."""

from django.db import transaction

from apps.pipeline.interfaces import PipelineInterface, TaskBackendUnavailable


def approval_queue():
    from apps.companies.interfaces import CompaniesInterface

    return [
        CompaniesInterface.pending_approval_payload(company)
        for company in CompaniesInterface.companies_awaiting_verification()
    ]


@transaction.atomic
def record_decision(company_id, actor, outcome, note=""):
    from apps.companies.interfaces import CompaniesInterface

    company = CompaniesInterface.company_or_error(company_id)
    decision = CompaniesInterface.record_verification_decision(
        company, actor, outcome, note=note
    )
    site = PipelineInterface.site_for_company(company.pk)
    if outcome == "approved":
        if site is None:
            site = PipelineInterface.onboard_site(company.pk, actor=actor)
        elif site.maintenance_state == site.MaintenanceState.SUSPENDED:
            PipelineInterface.resume_site(site, actor=actor)
        PipelineInterface.enqueue_site_pipeline(site.pk, actor=actor)
    elif site is not None:
        PipelineInterface.suspend_site(site, actor=actor)
    return company, decision, site


__all__ = ["approval_queue", "record_decision", "TaskBackendUnavailable"]
