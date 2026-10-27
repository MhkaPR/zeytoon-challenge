"""Runtime-tunables test (FR-043, SC-015).

Every tunable is read through ``admin_console.constants`` and takes effect after a
``PUT /api/v1/ops/settings`` change with no code change.
"""

import pytest
from constance.test import override_config

from admin_console import constants
from admin_console.plan_schema import PLAN_SCHEMA

pytestmark = pytest.mark.django_db


def test_settings_endpoint_round_trips_tunables(operator_client):
    response = operator_client.put(
        "/api/v1/ops/settings",
        {
            "values": {
                "REPLAY_PERIOD_HOURS": 12,
                "FAILURE_RATE_THRESHOLD": 0.25,
                "LABELING_ENABLED": True,
            }
        },
        format="json",
    )
    assert response.status_code == 200
    assert constants.replay_period_hours() == 12
    assert constants.failure_rate_threshold() == 0.25
    assert constants.labeling_enabled() is True


def test_cleaning_rules_take_effect_from_settings(operator_client):
    response = operator_client.put(
        "/api/v1/ops/settings",
        {"values": {"CLEANING_RULES": {"plan_name": {"replace": {"!": ""}}}}},
        format="json",
    )
    assert response.status_code == 200
    from admin_console import cleaning

    field = PLAN_SCHEMA["hosting"].field_map()["plan_name"]
    assert cleaning.clean_value(field, "Starter!")["value"] == "Starter"


@override_config(REPLAY_PERIOD_HOURS=6)
def test_constants_helpers_read_constance_not_module_state():
    assert constants.replay_period_hours() == 6
    assert constants.replay_batch_size() >= 1
    assert isinstance(constants.failure_rate_threshold(), float)
