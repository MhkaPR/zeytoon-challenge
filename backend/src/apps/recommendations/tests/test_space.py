import numpy as np
import pytest

from apps.recommendations import conf
from apps.recommendations.services.v1.features import PlanFeatureMapper
from apps.recommendations.services.v1.space import PlanSpace


def test_undeclared_attributes_are_masked():
    features = [
        PlanFeatureMapper().map({"id": 1, "values": {"price_amount": 10, "ram_amount": 4}}),
        PlanFeatureMapper().map({"id": 2, "values": {"price_amount": 20}}),
    ]
    space = PlanSpace(n_bins=3).fit(features)
    values, masks = space.transform(features)
    ram_index = space.names.index("ram")
    assert masks[0][ram_index] == 1.0
    assert masks[1][ram_index] == 0.0


def test_cold_start_prior_is_deterministic():
    features = [
        PlanFeatureMapper().map({"id": 1, "values": {"price_amount": 10}}),
        PlanFeatureMapper().map({"id": 2, "values": {"price_amount": 30}}),
    ]
    space = PlanSpace(n_bins=3).fit(features)
    values, masks = space.transform(features)
    first = space.prior(values, masks)
    second = space.prior(values, masks)
    assert np.array_equal(first, second)


def test_space_has_ten_semantic_dimensions():
    features = [
        PlanFeatureMapper().map(
            {"id": 1, "values": {"price_amount": 10, "plan_name": "سرور گیمینگ"}}
        ),
        PlanFeatureMapper().map(
            {"id": 2, "values": {"price_amount": 20, "plan_name": "هاست ایمیل"}}
        ),
    ]
    space = PlanSpace(n_bins=3).fit(features)
    values, masks = space.transform(features)
    semantic_names = [name for name in space.names if name.startswith("semantic_")]
    assert semantic_names == [f"semantic_{index}" for index in range(10)]
    assert values.shape == masks.shape
    assert values.shape[1] == len(space.names)


def test_version_changes_when_title_changes():
    first = [
        PlanFeatureMapper().map(
            {"id": 1, "values": {"price_amount": 10, "plan_name": "سرور گیمینگ"}}
        )
    ]
    second = [
        PlanFeatureMapper().map(
            {"id": 1, "values": {"price_amount": 10, "plan_name": "هاست ایمیل"}}
        )
    ]
    assert PlanSpace(n_bins=3).version(first) != PlanSpace(n_bins=3).version(second)


def test_version_changes_when_semantic_config_changes(monkeypatch):
    features = [
        PlanFeatureMapper().map(
            {"id": 1, "values": {"price_amount": 10, "plan_name": "سرور گیمینگ"}}
        )
    ]
    before = PlanSpace(n_bins=3).version(features)
    monkeypatch.setattr(conf, "semantic_dimensions", lambda: 5)
    after = PlanSpace(n_bins=3).version(features)
    assert before != after
