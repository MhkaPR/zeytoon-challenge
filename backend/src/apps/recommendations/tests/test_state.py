import numpy as np

from apps.recommendations.services.v1.state import InterestClusters, UserState


def test_stronger_signal_moves_more():
    values = np.array([1.0, 1.0])
    masks = np.array([1.0, 1.0])
    strong = UserState([0.0, 0.0])
    weak = UserState([0.0, 0.0])
    strong.update(values, masks, 0.3)
    weak.update(values, masks, 1.5)
    assert strong.x[0] > weak.x[0]


def test_repeated_signals_diminish():
    values = np.array([1.0])
    masks = np.array([1.0])
    state = UserState([0.0])
    state.update(values, masks, 1.0)
    first = state.x[0]
    state.update(values, masks, 1.0)
    second_delta = state.x[0] - first
    state.update(values, masks, 1.0)
    third_delta = state.x[0] - first - second_delta
    assert third_delta < second_delta


def test_flat_position_is_one_cluster():
    clusters = InterestClusters([0.1, 0.2])
    assert len(clusters.states) == 1
    assert np.allclose(clusters.states[0].x, [0.1, 0.2])


def test_numpy_positions_are_distinguished_from_a_flat_vector():
    single = InterestClusters(np.array([0.1, 0.2]))
    assert len(single.states) == 1
    assert np.allclose(single.states[0].x, [0.1, 0.2])

    multiple = InterestClusters(
        [np.array([0.0, 0.0]), np.array([1.0, 1.0])]
    )
    assert len(multiple.states) == 2
    assert np.allclose(multiple.states[1].x, [1.0, 1.0])


def test_near_signal_updates_nearest_cluster():
    clusters = InterestClusters(
        [[0.0, 0.0], [1.0, 1.0]], max_clusters=3, threshold=0.2
    )
    clusters.update(np.array([0.1, 0.1]), np.array([1.0, 1.0]), noise=0.8)
    assert len(clusters.states) == 2
    assert clusters.states[0].x[0] > 0.0
    assert np.allclose(clusters.states[1].x, [1.0, 1.0])


def test_far_signal_creates_new_cluster():
    clusters = InterestClusters(
        [[0.0, 0.0], [1.0, 1.0]], max_clusters=3, threshold=0.2
    )
    clusters.update(np.array([0.5, 0.5]), np.array([1.0, 1.0]), noise=0.8)
    assert len(clusters.states) == 3


def test_cluster_cap_evicts_least_confident():
    clusters = InterestClusters(
        [[0.0, 0.0], [1.0, 1.0]], max_clusters=2, threshold=0.2
    )
    clusters.update(np.array([0.5, 0.5]), np.array([1.0, 1.0]), noise=0.8)
    assert len(clusters.states) == 2


def test_inactive_cluster_fades_after_repeated_new_interest(monkeypatch):
    from apps.recommendations import conf

    monkeypatch.setattr(conf, "cluster_activity_decay", lambda: 0.5)
    monkeypatch.setattr(conf, "cluster_min_activity", lambda: 0.5)
    clusters = InterestClusters(
        [[0.0, 0.0], [1.0, 1.0]], max_clusters=4, threshold=0.2
    )

    for _ in range(3):
        clusters.update(np.array([0.0, 0.0]), np.array([1.0, 1.0]), noise=0.8)

    active = clusters.active_states()
    assert len(active) == 1
    assert np.allclose(active[0].x, [0.0, 0.0])


def test_low_activity_clusters_stay_visible_relative_to_top():
    clusters = InterestClusters(
        [[0.0, 0.0], [1.0, 1.0], [0.5, 0.5]],
        activities=[0.0038166509464209555, 4.99537955116124, 0.0007918252709265627],
        max_clusters=4,
        threshold=0.2,
    )

    active = clusters.active_states()

    assert len(active) == 3
    assert active[0].activity > active[1].activity > active[2].activity


def test_fully_stale_clusters_are_dropped_relative_to_top():
    clusters = InterestClusters(
        [[0.0, 0.0], [1.0, 1.0], [0.5, 0.5]],
        activities=[0.00001, 5.0, 0.00002],
        max_clusters=4,
        threshold=0.2,
    )

    active = clusters.active_states()

    assert len(active) == 1
    assert active[0].activity == 5.0
