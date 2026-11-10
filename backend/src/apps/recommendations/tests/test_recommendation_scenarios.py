"""End-to-end recommendation scenarios used for the presentation report.

Every test builds one situation a viewer can create and checks what the real
pipeline (signals -> state -> clustering -> ranking -> explanations) returns.

The synthetic catalogue has four clearly separated bands so the production
statistical gates (pattern size >= 30, lift >= 2.0, |MCC| >= 0.20, Fisher
p <= 0.05) can fire on their own, without relaxing any threshold:

* ``cheap``      (rows 0-29):   low price, low specs
* ``value``      (rows 30-59):  low/mid price, high specs
* ``overpriced`` (rows 60-89):  high-ish price, low specs (a deliberate decoy)
* ``premium``    (rows 90-119): high price, high specs
"""

from __future__ import annotations

import uuid
from io import StringIO

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.catalog.interfaces import CatalogInterface
from apps.recommendations import conf
from apps.recommendations.models import InterestProfile
from apps.recommendations.services.v1.ranking import RankingService
from apps.recommendations.services.v1.signals import SignalRecorder
from apps.recommendations.tests.factories import catalog

CHEAP = range(0, 30)
VALUE = range(30, 60)
OVERPRICED = range(60, 90)
PREMIUM = range(90, 120)

HIGH_SPECS = {"cpu": 64, "ram": 256, "disk": 4000}
LOW_SPECS = {"cpu": 1, "ram": 1, "disk": 10}


def _intent_catalog():
    plans = []
    for index in CHEAP:
        plans.append(
            {
                "price_amount": 10 + index,
                **LOW_SPECS,
                "plan_name": f"cheap {index}",
                "plan_type": "hosting",
            }
        )
    for index in VALUE:
        plans.append(
            {
                "price_amount": 100 + (index - 30),
                **HIGH_SPECS,
                "plan_name": f"value {index}",
                "plan_type": "virtual_server",
            }
        )
    for index in OVERPRICED:
        plans.append(
            {
                "price_amount": 500 + (index - 60),
                **LOW_SPECS,
                "plan_name": f"overpriced {index}",
                "plan_type": "hosting",
            }
        )
    for index in PREMIUM:
        plans.append(
            {
                "price_amount": 1000 + (index - 90),
                **HIGH_SPECS,
                "plan_name": f"premium {index}",
                "plan_type": "dedicated_server",
            }
        )
    return catalog(*plans)


def _click(records, plan_records, kind, indices, visitor, query=""):
    return SignalRecorder().record(
        plan_records,
        kind,
        [records[index].pk for index in indices],
        query=query,
        visitor_id=visitor,
    )


def _intents(result):
    return [item["intent"] for item in result["explanations"]]


# --------------------------------------------------------------------------- #
# Cold start and intent detection
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_scenario_cold_start_returns_exploring_with_plans():
    _intent_catalog()
    plan_records = CatalogInterface.published_plan_records()

    result = RankingService().suggest_with_explanations(plan_records, limit=10)

    assert result["plan_ids"]
    assert result["explanations"]
    assert _intents(result) == ["exploring"]
    assert result["explanations"][0]["message"].endswith("؟")


@pytest.mark.django_db
def test_scenario_premium_clicks_detect_premium_intent():
    records = _intent_catalog()
    plan_records = CatalogInterface.published_plan_records()
    visitor = uuid.uuid4()
    _click(records, plan_records, "destination_visit", list(PREMIUM)[:5], visitor)

    result = RankingService().suggest_with_explanations(
        plan_records, visitor_id=visitor, limit=15
    )

    assert _intents(result)[0] == "premium"
    assert "پرقدرت" in result["explanations"][0]["message"]


@pytest.mark.django_db
def test_scenario_cheap_clicks_detect_cheap_intent():
    records = _intent_catalog()
    plan_records = CatalogInterface.published_plan_records()
    visitor = uuid.uuid4()
    _click(records, plan_records, "destination_visit", list(CHEAP)[:5], visitor)

    result = RankingService().suggest_with_explanations(
        plan_records, visitor_id=visitor, limit=15
    )

    assert _intents(result)[0] == "cheap"
    assert "اقتصادی" in result["explanations"][0]["message"]


@pytest.mark.django_db
def test_scenario_value_clicks_detect_value_intent():
    records = _intent_catalog()
    plan_records = CatalogInterface.published_plan_records()
    visitor = uuid.uuid4()
    _click(records, plan_records, "destination_visit", list(VALUE)[:5], visitor)

    result = RankingService().suggest_with_explanations(
        plan_records, visitor_id=visitor, limit=15
    )

    assert _intents(result)[0] == "value"
    assert "نسبت امکانات به قیمت" in result["explanations"][0]["message"]


@pytest.mark.django_db
def test_scenario_overpriced_clicks_do_not_masquerade_as_value():
    records = _intent_catalog()
    plan_records = CatalogInterface.published_plan_records()
    visitor = uuid.uuid4()
    _click(records, plan_records, "destination_visit", list(OVERPRICED)[:5], visitor)

    result = RankingService().suggest_with_explanations(
        plan_records, visitor_id=visitor, limit=15
    )

    assert "value" not in _intents(result)
    assert _intents(result)[0] == "exploring"


# --------------------------------------------------------------------------- #
# Signals other than outbound clicks
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_scenario_search_impressions_detect_intent_without_clicks():
    records = _intent_catalog()
    plan_records = CatalogInterface.published_plan_records()
    visitor = uuid.uuid4()
    _click(
        records,
        plan_records,
        "search_impression",
        list(PREMIUM)[:10],
        visitor,
        query="dedicated",
    )

    result = RankingService().suggest_with_explanations(
        plan_records, visitor_id=visitor, limit=15
    )

    assert _intents(result)[0] == "premium"


@pytest.mark.django_db
def test_scenario_details_views_detect_intent_without_outbound_clicks():
    records = _intent_catalog()
    plan_records = CatalogInterface.published_plan_records()
    visitor = uuid.uuid4()
    _click(records, plan_records, "details_view", list(PREMIUM)[:5], visitor)

    result = RankingService().suggest_with_explanations(
        plan_records, visitor_id=visitor, limit=15
    )

    assert _intents(result)[0] == "premium"


@pytest.mark.django_db
def test_scenario_search_only_cheap_intent():
    records = _intent_catalog()
    plan_records = CatalogInterface.published_plan_records()
    visitor = uuid.uuid4()
    _click(
        records,
        plan_records,
        "search_impression",
        list(CHEAP)[:10],
        visitor,
        query="ارزان",
    )

    result = RankingService().suggest_with_explanations(
        plan_records, visitor_id=visitor, limit=15
    )

    assert _intents(result)[0] == "cheap"


# --------------------------------------------------------------------------- #
# Multiple interests and duplicate suppression
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_scenario_two_interests_produce_two_reasons():
    records = _intent_catalog()
    plan_records = CatalogInterface.published_plan_records()
    visitor = uuid.uuid4()
    _click(records, plan_records, "destination_visit", list(CHEAP)[:5], visitor)
    _click(records, plan_records, "destination_visit", list(PREMIUM)[:5], visitor)

    result = RankingService().suggest_with_explanations(
        plan_records, visitor_id=visitor, limit=20
    )

    assert {"cheap", "premium"}.issubset(set(_intents(result)))
    assert len(result["explanations"]) >= 2


@pytest.mark.django_db
def test_scenario_repeated_interest_is_merged_into_one_reason():
    records = _intent_catalog()
    plan_records = CatalogInterface.published_plan_records()
    visitor = uuid.uuid4()
    _click(records, plan_records, "destination_visit", list(PREMIUM)[:5], visitor)
    _click(records, plan_records, "destination_visit", list(PREMIUM)[5:10], visitor)

    result = RankingService().suggest_with_explanations(
        plan_records, visitor_id=visitor, limit=20
    )

    assert _intents(result).count("premium") == 1


@pytest.mark.django_db
def test_scenario_merged_rows_never_repeat_a_plan():
    records = _intent_catalog()
    plan_records = CatalogInterface.published_plan_records()
    visitor = uuid.uuid4()
    _click(records, plan_records, "destination_visit", list(PREMIUM)[:5], visitor)
    _click(records, plan_records, "destination_visit", list(CHEAP)[:5], visitor)

    result = RankingService().suggest_with_explanations(
        plan_records, visitor_id=visitor, limit=20
    )

    all_ids = [
        plan_id
        for explanation in result["explanations"]
        for plan_id in explanation["plan_ids"]
    ]
    assert len(all_ids) == len(set(all_ids))


# --------------------------------------------------------------------------- #
# Resource eligibility
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_scenario_missing_resource_plans_are_not_suggested():
    records = catalog(
        {"price_amount": 10, "plan_name": "license only"},
        {
            "price_amount": 100,
            "cpu": 8,
            "ram": 32,
            "disk": 500,
            "plan_name": "real server",
        },
    )
    plan_records = CatalogInterface.published_plan_records()

    suggested = RankingService().suggest(plan_records, limit=10)

    assert records[1].pk in suggested
    assert records[0].pk not in suggested


@pytest.mark.django_db
def test_scenario_partial_resource_plan_stays_eligible():
    records = catalog(
        {"price_amount": 10, "plan_name": "no resources"},
        {"price_amount": 20, "ram": 8, "plan_name": "ram only"},
        {
            "price_amount": 30,
            "cpu": 2,
            "ram": 8,
            "disk": 100,
            "plan_name": "full server",
        },
    )
    plan_records = CatalogInterface.published_plan_records()

    suggested = RankingService().suggest(plan_records, limit=10)

    assert records[1].pk in suggested
    assert records[0].pk not in suggested


@pytest.mark.django_db
def test_scenario_min_resource_dimensions_is_configurable(monkeypatch):
    monkeypatch.setattr(conf, "min_resource_dimensions", lambda: 2)
    records = catalog(
        {"price_amount": 20, "ram": 8, "plan_name": "ram only"},
        {
            "price_amount": 30,
            "cpu": 2,
            "ram": 8,
            "disk": 100,
            "plan_name": "full server",
        },
    )
    plan_records = CatalogInterface.published_plan_records()

    suggested = RankingService().suggest(plan_records, limit=10)

    assert records[1].pk in suggested
    assert records[0].pk not in suggested


# --------------------------------------------------------------------------- #
# Profile lifecycle: decay, isolation, caps
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_scenario_recent_interest_dominates_old_one():
    records = _intent_catalog()
    plan_records = CatalogInterface.published_plan_records()
    visitor = uuid.uuid4()
    _click(records, plan_records, "destination_visit", list(PREMIUM)[:5], visitor)
    for _ in range(12):
        _click(records, plan_records, "destination_visit", list(CHEAP)[:1], visitor)

    profile = InterestProfile.objects.get(visitor_id=visitor)
    result = RankingService().suggest_with_explanations(
        plan_records, visitor_id=visitor, limit=20
    )

    assert len(profile.activity_profile) >= 2
    assert max(profile.activity_profile) > min(profile.activity_profile)
    assert "cheap" in _intents(result)


@pytest.mark.django_db
def test_scenario_profiles_are_isolated_per_visitor():
    records = _intent_catalog()
    plan_records = CatalogInterface.published_plan_records()
    cheap_visitor = uuid.uuid4()
    premium_visitor = uuid.uuid4()
    _click(records, plan_records, "destination_visit", list(CHEAP)[:5], cheap_visitor)
    _click(
        records, plan_records, "destination_visit", list(PREMIUM)[:5], premium_visitor
    )

    cheap_result = RankingService().suggest_with_explanations(
        plan_records, visitor_id=cheap_visitor, limit=10
    )
    premium_result = RankingService().suggest_with_explanations(
        plan_records, visitor_id=premium_visitor, limit=10
    )

    assert _intents(cheap_result)[0] == "cheap"
    assert _intents(premium_result)[0] == "premium"


@pytest.mark.django_db
def test_scenario_signal_cap_rejects_flood(monkeypatch):
    records = _intent_catalog()
    plan_records = CatalogInterface.published_plan_records()
    visitor = uuid.uuid4()
    monkeypatch.setattr(conf, "signal_cap_per_minute", lambda: 2)

    accepted = 0
    for _ in range(5):
        result = _click(
            records, plan_records, "destination_visit", list(CHEAP)[:1], visitor
        )
        accepted += result["accepted"]

    assert accepted == 2


# --------------------------------------------------------------------------- #
# Public API contract
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_scenario_suggested_endpoint_returns_plans_and_reasons():
    records = _intent_catalog()
    plan_records = CatalogInterface.published_plan_records()
    visitor = uuid.uuid4()
    _click(records, plan_records, "destination_visit", list(PREMIUM)[:5], visitor)

    response = APIClient().get(
        "/api/v1/catalog/plans/suggested",
        HTTP_X_VISITOR_ID=str(visitor),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]
    assert payload["explanations"]
    assert payload["explanations"][0]["intent"] == "premium"


@pytest.mark.django_db
def test_scenario_invalid_visitor_id_falls_back_to_cold_start():
    _intent_catalog()

    response = APIClient().get(
        "/api/v1/catalog/plans/suggested",
        HTTP_X_VISITOR_ID="not-a-uuid",
    )

    assert response.status_code == 200
    assert response.json()["data"]


@pytest.mark.django_db
def test_scenario_suggestions_are_deterministic():
    records = _intent_catalog()
    plan_records = CatalogInterface.published_plan_records()
    visitor = uuid.uuid4()
    _click(records, plan_records, "destination_visit", list(PREMIUM)[:5], visitor)

    first = RankingService().suggest_with_explanations(
        plan_records, visitor_id=visitor, limit=15
    )
    second = RankingService().suggest_with_explanations(
        plan_records, visitor_id=visitor, limit=15
    )

    assert first == second


# --------------------------------------------------------------------------- #
# Simulation command used in live demos
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_scenario_simulation_command_reports_intent():
    _intent_catalog()
    out = StringIO()

    call_command(
        "simulate_recommendations",
        "--visitor-id",
        str(uuid.uuid4()),
        "--plan-type",
        "dedicated_server",
        "--count",
        "5",
        "--top",
        "10",
        stdout=out,
    )

    output = out.getvalue()
    assert "suggested plans" in output
    assert "premium" in output
