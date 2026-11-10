"""Behaviour tests for per-cluster feature attribution."""

import uuid

import numpy as np
import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.recommendations import conf
from apps.recommendations.services.v1.ranking import RankingService
from apps.recommendations.services.v1.reasons import FeatureReasoner
from apps.recommendations.services.v1.signals import SignalRecorder
from apps.recommendations.services.v1.space import NumericBinner
from apps.recommendations.services.v1.store import PlanSpaceProvider
from apps.recommendations.tests.factories import catalog


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


def _records(record_list):
    return [
        {"id": record.pk, "values": record.values, "published_at": record.published_at}
        for record in record_list
    ]


def _signal(records, visitor, plan_ids, kind="details_view"):
    return SignalRecorder().record(
        _records(records), kind, plan_ids, visitor_id=visitor
    )


def test_revert_interpolated_only_returns_observed_values():
    binner = NumericBinner([1, 2, 3, 4], 4)
    pairs = [(0.0, 1.0), (0.3, 2.0), (0.6, 3.0), (1.0, 4.0)]

    assert binner.revert_interpolated(0.0, pairs) == 1.0
    assert binner.revert_interpolated(1.0, pairs) == 4.0
    midpoint = binner.revert_interpolated(0.45, pairs)
    assert 2.0 < midpoint < 3.0


@pytest.mark.django_db
def test_ram_heavy_interest_explains_ram_first():
    plans = [
        {
            "ram_amount": 1 + (index % 10) * 2,
            "price_amount": 1000 + index * 100,
            "plan_name": f"plan {index}",
        }
        for index in range(30)
    ]
    records = catalog(*plans)
    visitor = uuid.uuid4()
    high_ram = [record.pk for record in records if record.values["ram_amount"] >= 15]
    _signal(records, visitor, high_ram)

    result = RankingService().suggest_with_reasons(
        _records(records), visitor_id=visitor, limit=20
    )

    assert result["explanations"]
    top = result["explanations"][0]
    assert top["reasons"][0]["feature"] == "ram"
    low, high = top["reasons"][0]["real_range"]
    representative = next(
        record for record in records if record.pk == top["representative_plan_id"]
    )
    ram = representative.values["ram_amount"]
    assert low <= ram <= high


@pytest.mark.django_db
def test_representative_plan_is_in_suggested_list():
    records = catalog(
        *[
            {"price_amount": 10 + index, "plan_name": f"plan {index}"}
            for index in range(25)
        ]
    )
    visitor = uuid.uuid4()
    _signal(records, visitor, [records[0].pk])

    result = RankingService().suggest_with_reasons(
        _records(records), visitor_id=visitor, limit=20
    )

    suggested = set(result["plan_ids"])
    for explanation in result["explanations"]:
        assert explanation["representative_plan_id"] in suggested


@pytest.mark.django_db
def test_outlier_does_not_widen_ram_band_to_full_catalog():
    plans = [
        {
            "ram_amount": 4 + (index % 4),
            "price_amount": 1000 + index,
            "plan_name": f"normal {index}",
        }
        for index in range(20)
    ]
    plans.append(
        {"ram_amount": 4096, "price_amount": 999999, "plan_name": "extreme outlier"}
    )
    records = catalog(*plans)
    visitor = uuid.uuid4()
    _signal(records, visitor, [record.pk for record in records[:6]])

    result = RankingService().suggest_with_reasons(
        _records(records), visitor_id=visitor, limit=20
    )
    ram_reason = next(
        reason
        for reason in result["explanations"][0]["reasons"]
        if reason["feature"] == "ram"
    )
    low, high = ram_reason["real_range"]
    assert high - low < 100


@pytest.mark.django_db
def test_clusters_are_explained_independently():
    records = catalog(
        *[
            {
                "ram_amount": 1 + index,
                "storage_amount": 10 + index * 5,
                "price_amount": 1000 + index * 50,
                "plan_name": f"plan {index}",
            }
            for index in range(20)
        ]
    )
    bundle = PlanSpaceProvider().load(_records(records))
    reasoner = FeatureReasoner(bundle)
    ram_index = bundle["space"].names.index("ram")
    disk_index = bundle["space"].names.index("disk")

    ram_position = np.full(bundle["values"].shape[1], 0.5)
    ram_position[ram_index] = 0.9
    disk_position = np.full(bundle["values"].shape[1], 0.5)
    disk_position[disk_index] = 0.9

    disk_before = reasoner.explain_cluster(disk_position, 1)
    changed_ram = ram_position.copy()
    changed_ram[ram_index] = 0.1
    reasoner.explain_cluster(changed_ram, 0)
    disk_after = reasoner.explain_cluster(disk_position, 1)

    assert disk_before["reasons"] == disk_after["reasons"]


@pytest.mark.django_db
def test_threshold_gate_suppresses_weak_reasons(monkeypatch):
    records = catalog(
        {"price_amount": 10, "plan_name": "plan one"},
        {"price_amount": 30, "plan_name": "plan two"},
    )
    bundle = PlanSpaceProvider().load(_records(records))
    monkeypatch.setattr(conf, "explain_f1_threshold", lambda: 0.99)

    explanation = FeatureReasoner(bundle).explain_cluster(
        np.full(bundle["values"].shape[1], 0.5), 0
    )

    assert explanation["reasons"] == []


@pytest.mark.django_db
def test_cold_start_viewer_has_no_reasons():
    records = catalog({"price_amount": 10, "plan_name": "plan"})
    visitor = uuid.uuid4()

    result = RankingService().suggest_with_reasons(
        _records(records), visitor_id=visitor
    )

    assert result["explanations"] == []


@pytest.mark.django_db
def test_reasons_are_deterministic():
    records = catalog(
        {"ram_amount": 8, "price_amount": 10, "plan_name": "gaming server"},
        {"ram_amount": 2, "price_amount": 30, "plan_name": "email host"},
        {"ram_amount": 4, "price_amount": 50, "plan_name": "wordpress plan"},
    )
    visitor = uuid.uuid4()
    _signal(records, visitor, [records[0].pk])

    first = RankingService().suggest_with_reasons(
        _records(records), visitor_id=visitor
    )
    second = RankingService().suggest_with_reasons(
        _records(records), visitor_id=visitor
    )

    assert first["explanations"] == second["explanations"]


@pytest.mark.django_db
def test_suggested_endpoint_embeds_explanations():
    records = catalog(
        *[
            {
                "ram_amount": 2 + (index % 6) * 2,
                "price_amount": 1000 + index * 100,
                "plan_name": f"plan {index}",
            }
            for index in range(20)
        ]
    )
    visitor = uuid.uuid4()
    _signal(records, visitor, [record.pk for record in records if record.values["ram_amount"] >= 10])

    response = APIClient().get(
        "/api/v1/catalog/plans/suggested",
        HTTP_X_VISITOR_ID=str(visitor),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]
    assert body["explanations"]
    explanation = body["explanations"][0]
    assert explanation["representative_plan_id"] in {
        plan["id"] for plan in body["data"]
    }
    assert explanation["reasons"]
