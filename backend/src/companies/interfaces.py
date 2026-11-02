"""Public interface for the companies module (Constitution Principle V).

Other modules MUST import company behavior through this module only; direct access to the
companies tables is forbidden. The panel surface is internal to ``companies`` and does not
need an interface entry.
"""

from companies import selectors, services


class CompaniesInterface:
    """The single sanctioned entry point into the companies module."""

    # --- read ---
    @staticmethod
    def list_companies(user):
        return selectors.list_owned_companies(user)

    @staticmethod
    def get_owned_company(user, company_id):
        return selectors.owned_company_or_error(user, company_id)

    @staticmethod
    def step_progress(company):
        return selectors.step_progress_payload(company)

    @staticmethod
    def current_step(company):
        return selectors.current_step(company)

    @staticmethod
    def can_manage_plans(company):
        return services.can_manage_plans(company)

    @staticmethod
    def companies_awaiting_verification():
        return selectors.companies_awaiting_verification()

    @staticmethod
    def pending_approval_payload(company):
        return selectors.pending_approval_payload(company)

    @staticmethod
    def company_or_error(company_id):
        return selectors.company_or_error(company_id)

    # --- write ---
    @staticmethod
    def record_verification_decision(company, actor, outcome, note=""):
        return services.record_verification_decision(company, actor, outcome, note=note)


__all__ = ["CompaniesInterface"]
