"""Plan-schema tests (US6, FR-027, FR-030)."""

import dataclasses

import pytest

from admin_console import plan_schema


def test_schema_carries_the_plan_type_dimension():
    assert set(plan_schema.PLAN_SCHEMA) >= {"hosting", "cdn", "virtual_server"}
    for key, plan in plan_schema.PLAN_SCHEMA.items():
        assert plan.key == key
        assert plan.fields  # every plan type has at least one field


def test_required_keys_match_the_completeness_gate():
    for key, plan in plan_schema.PLAN_SCHEMA.items():
        expected = {f.key for f in plan.fields if f.required}
        assert plan_schema.required_keys(key) == expected
        assert plan.required_keys() == expected
        # Required keys are always a subset of all declared fields.
        assert expected <= plan_schema.all_field_keys(key)


def test_schema_is_immutable_and_code_defined():
    plan = plan_schema.PLAN_SCHEMA["hosting"]
    with pytest.raises(dataclasses.FrozenInstanceError):
        plan.key = "changed"


def test_unknown_plan_type_has_no_required_keys():
    assert plan_schema.required_keys("nope") == set()
    assert plan_schema.all_field_keys("nope") == set()
    assert plan_schema.get_plan_type("nope") is None
