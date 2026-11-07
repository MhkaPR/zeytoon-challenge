import numpy as np
import pytest

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
