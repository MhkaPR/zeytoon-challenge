import json
from io import StringIO

import pytest
from django.core.management import call_command

from apps.recommendations.tests.factories import catalog


@pytest.mark.django_db
def test_simulation_command_replays_signals_and_prints_explanations():
    catalog(
        {
            "price_amount": 100,
            "cpu": 8,
            "ram": 32,
            "disk": 500,
            "plan_name": "dedicated",
            "plan_type": "dedicated_server",
        },
        {
            "price_amount": 50,
            "cpu": 2,
            "ram": 4,
            "disk": 50,
            "plan_name": "cheap",
            "plan_type": "hosting",
        },
    )
    out = StringIO()

    call_command(
        "simulate_recommendations",
        "--count",
        "5",
        "--plan-type",
        "dedicated_server",
        "--min-ram",
        "16",
        "--keep",
        stdout=out,
    )

    text = out.getvalue()
    assert "profile: signals=5" in text
    assert "explanations:" in text
    assert "intent=" in text


@pytest.mark.django_db
def test_simulation_command_emits_json():
    catalog(
        {
            "price_amount": 100,
            "cpu": 8,
            "ram": 32,
            "disk": 500,
            "plan_name": "dedicated",
            "plan_type": "dedicated_server",
        }
    )
    out = StringIO()

    call_command(
        "simulate_recommendations",
        "--count",
        "3",
        "--json",
        stdout=out,
    )

    payload = json.loads(out.getvalue())
    assert payload["profile"]["signal_count"] == 3
    assert payload["clusters"]
    assert payload["explanations"]


@pytest.mark.django_db
def test_query_implies_search_impression_and_filters_plans():
    catalog(
        {
            "price_amount": 100,
            "cpu": 2,
            "ram": 4,
            "disk": 50,
            "plan_name": "هاست وردپرس",
            "plan_type": "hosting",
        },
        {
            "price_amount": 200,
            "cpu": 8,
            "ram": 32,
            "disk": 500,
            "plan_name": "dedicated",
            "plan_type": "dedicated_server",
        },
    )
    out = StringIO()

    call_command(
        "simulate_recommendations",
        "--query",
        "وردپرس",
        "--count",
        "2",
        "--json",
        stdout=out,
    )

    payload = json.loads(out.getvalue())
    assert payload["kind"] == "search_impression"
    assert {plan["name"] for plan in payload["simulated_plans"]} == {
        "هاست وردپرس"
    }
