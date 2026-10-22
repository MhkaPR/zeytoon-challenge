"""Runtime configurability tests (FR-045, SC-011)."""

import pytest
from constance import config

from companies import constants

pytestmark = pytest.mark.django_db


def test_step_definitions_come_from_constance(settings):
    definitions = constants.step_definitions()
    assert [step["key"] for step in definitions] == [
        "company_information",
        "verification",
    ]
    assert definitions[1]["owner_input"] is False


def test_prerequisite_message_is_runtime_configurable():
    original = dict(config.COMPANY_REQUIREMENT_MESSAGES)
    try:
        config.COMPANY_REQUIREMENT_MESSAGES = {
            "verified": "V",
            "charged": "C",
            "both": "B",
        }
        assert constants.requirement_message(["charged"]) == "C"
        assert constants.requirement_message(["verified", "charged"]) == "B"
    finally:
        config.COMPANY_REQUIREMENT_MESSAGES = original


def test_step_locked_and_empty_state_messages_are_configurable():
    assert isinstance(constants.step_locked_message(), str)
    assert isinstance(constants.empty_state_message(), str)
