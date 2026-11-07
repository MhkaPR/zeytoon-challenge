import numpy as np

from apps.recommendations.services.v1.state import UserState


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
