"""Runtime-tunable constants for the companies feature (Principle XIII, FR-045).

Every value lives in the database-backed django-constance configuration declared in
``config/settings.py`` (``CONSTANCE_CONFIG``), so operators can change it from the Django
admin at runtime without editing code (SC-011). To change a value: open the Django admin,
navigate to Constance, edit the constant, and save — services read it through
``constance.config`` on the next request.

This feature deliberately declares **no** duplicate-signal constant: duplicate-company
detection lives in the admin panel (FR-042).
"""

from constance import config

STEP_KEY_COMPANY_INFORMATION = "company_information"
STEP_KEY_VERIFICATION = "verification"


def step_definitions():
    """Return the ordered registration step definitions (FR-011)."""
    return list(config.COMPANY_STEP_DEFINITIONS)


def step_keys():
    """Return the step keys in configured order."""
    return [step["key"] for step in step_definitions()]


def step_locked_message():
    return str(config.COMPANY_STEP_LOCKED_MESSAGE)


def empty_state_message():
    return str(config.COMPANY_EMPTY_STATE_MESSAGE)
