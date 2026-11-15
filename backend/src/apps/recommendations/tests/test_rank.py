import uuid
from types import SimpleNamespace

import numpy as np
import pytest

from apps.recommendations.models import InterestProfile
from apps.recommendations.services.v1.rank import RankService


class StaticProvider:
    def __init__(self, bundle):
        self.bundle = bundle

    def load(self, records):
        return self.bundle


def _bundle(values, ids, published_at=None, masks=None):
    values = np.asarray(values, dtype=float)
    masks = np.ones_like(values) if masks is None else np.asarray(masks, dtype=float)
    return {
        "values": values,
        "masks": masks,
        "ids": list(ids),
        "published_at": published_at or [""] * len(ids),
        "space": SimpleNamespace(names=[f"d{i}" for i in range(values.shape[1])]),
    }


def _seed(visitor, positions, uncertainties=None, updated=None, counts=None):
    uncertainties = uncertainties or [[1.0] * len(row) for row in positions]
    InterestProfile.objects.create(
        visitor_id=visitor,
        position=[list(row) for row in positions],
        uncertainty=[list(row) for row in uncertainties],
        node_ids=[str(uuid.uuid4()) for _ in positions],
        node_updated_at=updated or ["2026-01-01T00:00:00+00:00"] * len(positions),
        node_signal_counts=counts or [0] * len(positions),
        activity_profile=[1.0] * len(positions),
    )


@pytest.mark.django_db
def test_empty_node_set_returns_empty_result():
    bundle = _bundle([[0.0, 0.0]], [1])
    result = RankService().rank(
        uuid.uuid4(), StaticProvider(bundle), [], threshold=0.35
    )
    assert result == []


@pytest.mark.django_db
def test_all_plans_above_threshold_yield_empty_node_list():
    visitor = uuid.uuid4()
    _seed(visitor, [[0.0, 0.0]])
    bundle = _bundle([[1.0, 1.0], [0.9, 0.9]], [1, 2])

    result = RankService().rank(visitor, StaticProvider(bundle), [], 0.35)

    assert len(result) == 1
    assert result[0].plans == []


@pytest.mark.django_db
def test_all_plans_below_threshold_are_ordered_deterministically():
    visitor = uuid.uuid4()
    _seed(visitor, [[0.0, 0.0]])
    bundle = _bundle(
        [[0.1, 0.1], [0.1, 0.1], [0.2, 0.2]],
        [1, 2, 3],
        published_at=["2020-01-01", "2021-01-01", "2020-01-01"],
    )

    result = RankService().rank(visitor, StaticProvider(bundle), [], 0.35)

    # Equal distance: newest published_at first, then id.
    assert [plan.plan_id for plan in result[0].plans] == [2, 1, 3]


@pytest.mark.django_db
def test_masked_distance_uses_only_declared_dimensions():
    visitor = uuid.uuid4()
    _seed(visitor, [[0.0, 0.0]])
    bundle = _bundle(
        [[0.0, 1.0], [0.0, 0.3]],
        [1, 2],
        masks=[[1.0, 0.0], [1.0, 1.0]],
    )

    result = RankService().rank(visitor, StaticProvider(bundle), [], 0.35)

    # Plan 1 differs on dimension 1, but declares only dimension 0 -> distance 0.
    assert [plan.plan_id for plan in result[0].plans] == [1, 2]


@pytest.mark.django_db
def test_rank_does_not_mutate_nodes():
    visitor = uuid.uuid4()
    _seed(visitor, [[0.0, 0.0]])
    before = InterestProfile.objects.get(visitor_id=visitor)
    snapshot = (list(before.position), list(before.uncertainty))
    bundle = _bundle([[0.1, 0.1]], [1])

    RankService().rank(visitor, StaticProvider(bundle), [], 0.35)

    after = InterestProfile.objects.get(visitor_id=visitor)
    assert (list(after.position), list(after.uncertainty)) == snapshot
    assert after.node_updated_at == before.node_updated_at
    assert after.node_signal_counts == before.node_signal_counts
