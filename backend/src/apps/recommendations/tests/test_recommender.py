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


def test_cluster_recency_outranks_publication_time():
    ordered = Recommender.order_by_cluster(
        [1, 2, 3, 4],
        np.array([0.1, 0.1, 0.1, 0.1]),
        [
            "2026-01-01T00:00:00Z",
            "2026-02-01T00:00:00Z",
            "2026-03-01T00:00:00Z",
            "2026-04-01T00:00:00Z",
        ],
        [1, 0, 1, 0],
    )
    # Cluster 0 (ranks 2 and 4) sorts before cluster 1; newest wins within a cluster.
    assert ordered == [4, 2, 3, 1]
