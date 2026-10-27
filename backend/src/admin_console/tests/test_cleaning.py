"""Cleaning-engine tests (US7, FR-032, FR-033, FR-043, SC-011)."""

import pytest

from admin_console import cleaning
from admin_console.plan_schema import PLAN_SCHEMA

pytestmark = pytest.mark.django_db

HOSTING_REQUIRED = (
    "plan_name",
    "storage_amount",
    "storage_unit",
    "ram_amount",
    "cpu_cores",
    "bandwidth_amount",
    "price_amount",
    "billing_period",
)


def test_unit_and_number_rules_standardize_values():
    field = PLAN_SCHEMA["hosting"].field_map()["storage_amount"]
    cleaned = cleaning.clean_value(field, "1.5 TB")
    assert cleaned["outcome"] == cleaning.CLEAN
    # data_size base is MB: 1.5 TB -> 1_500_000 MB.
    assert cleaned["value"] == 1_500_000.0

    gigabytes = cleaning.clean_value(field, "۲۰ GB")
    assert gigabytes["value"] == 20_000.0


def test_currency_and_enum_rules_standardize_values():
    price = PLAN_SCHEMA["hosting"].field_map()["price_amount"]
    cleaned = cleaning.clean_value(price, "۱٬۲۳۴ تومان")
    assert cleaned["outcome"] == cleaning.CLEAN
    # currency base is IRR; TOMAN -> x10.
    assert cleaned["value"] == 12_340.0

    period = PLAN_SCHEMA["hosting"].field_map()["billing_period"]
    assert cleaning.clean_value(period, "Monthly")["value"] == "monthly"


def test_version_and_category_helpers_are_case_insensitive():
    field = PLAN_SCHEMA["cdn"].field_map()["traffic_amount"]
    assert cleaning.clean_value(field, "10gb")["value"] == 10_000.0


def test_automatically_cleanable_record_needs_no_operator_action():
    cleaned, exceptions = cleaning.clean_record(
        "hosting",
        {
            "plan_name": "  Starter  ",
            "storage_amount": "10 GB",
            "storage_unit": "GB",
            "ram_amount": "512 MB",
            "cpu_cores": "2",
            "bandwidth_amount": "1 TB",
            "price_amount": "100,000",
            "billing_period": "yearly",
        },
    )
    assert exceptions == {}
    assert cleaned["plan_name"] == "Starter"
    assert cleaned["storage_amount"] == 10_000.0
    assert cleaned["price_amount"] == 100_000.0
    assert cleaned["billing_period"] == "yearly"


def test_only_unresolvable_values_are_surfaced_as_exceptions():
    cleaned, exceptions = cleaning.clean_record(
        "hosting",
        {
            "plan_name": "Starter",
            "storage_amount": "not-a-size",
            "storage_unit": "GB",
            "ram_amount": "512 MB",
            "cpu_cores": "2",
            "bandwidth_amount": "1 TB",
            "price_amount": "100000",
            "billing_period": "yearly",
        },
    )
    assert set(exceptions) == {"storage_amount"}
    assert exceptions["storage_amount"] == "unparsable_number"
    # Every other field is still cleaned, so the record stays publishable.
    assert cleaned["plan_name"] == "Starter"
    assert cleaned["ram_amount"] == 512.0
    assert "storage_amount" not in cleaned


def test_unknown_unit_and_category_are_exceptions():
    field = PLAN_SCHEMA["hosting"].field_map()["storage_amount"]
    missing = cleaning.clean_value(field, "")
    assert missing["outcome"] == cleaning.EXCEPTION
    assert missing["reason"] == "missing_required"

    period = PLAN_SCHEMA["hosting"].field_map()["billing_period"]
    unknown = cleaning.clean_value(period, "fortnightly")
    assert unknown["outcome"] == cleaning.EXCEPTION
    assert unknown["reason"].startswith("unknown_category")


def test_rule_values_come_from_constance(db, settings):
    """Change a constance rule and the engine follows it (FR-043, Principle XIII)."""
    field = PLAN_SCHEMA["hosting"].field_map()["cpu_cores"]
    # Numeric with no unit family: a plain decimal parses.
    assert cleaning.clean_value(field, "4")["value"] == 4.0

    field = PLAN_SCHEMA["hosting"].field_map()["plan_name"]
    assert cleaning.clean_value(field, "Starter!")["value"] == "Starter!"

    from constance import config

    original = dict(config.CLEANING_RULES or {})
    config.CLEANING_RULES = {
        **original,
        "plan_name": {"replace": {"!": ""}},
    }
    try:
        assert cleaning.clean_value(field, "Starter!")["value"] == "Starter"
    finally:
        config.CLEANING_RULES = original
