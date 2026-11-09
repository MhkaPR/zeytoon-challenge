import numpy as np

from apps.recommendations.services.v1.recommender import Recommender


def test_order_is_stable_on_ties():
    ordered = Recommender.order([3, 1, 2], np.array([1.0, 1.0, 1.0]), ["", "", ""])
    assert ordered == [1, 2, 3]


def test_newest_wins_tie():
    ordered = Recommender.order(
        [1, 2],
        np.array([1.0, 1.0]),
        ["2026-01-01T00:00:00Z", "2026-02-01T00:00:00Z"],
    )
    assert ordered == [2, 1]
