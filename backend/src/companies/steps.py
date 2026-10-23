"""Registration step locking helpers (FR-008)."""

from accounts.exceptions import ApiError
from companies import constants
from companies.models import CompanyStepProgress


def assert_step_enterable(company, step_key):
    """Raise ``step_locked`` unless the step is open and its predecessor is approved."""
    if step_key not in constants.step_keys():
        raise ApiError("unknown_step", "Unknown registration step.", http_status=404)

    row = CompanyStepProgress.objects.filter(
        company=company, step_key=step_key
    ).first()
    if row is None or row.state == CompanyStepProgress.State.LOCKED:
        raise ApiError(
            "step_locked",
            constants.step_locked_message(),
            http_status=403,
        )

    definitions = constants.step_definitions()
    index = constants.step_keys().index(step_key)
    if index == 0:
        return row
    previous_key = definitions[index - 1]["key"]
    previous = CompanyStepProgress.objects.filter(
        company=company, step_key=previous_key
    ).first()
    if previous is None or previous.state != CompanyStepProgress.State.APPROVED:
        raise ApiError(
            "step_locked",
            constants.step_locked_message(),
            http_status=403,
        )
    return row
