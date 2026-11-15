from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from apps.recommendations.services.v1.kalman import KalmanModule

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def test_decay_grows_uncertainty_by_rate_times_hours():
    last = NOW - timedelta(hours=10)
    _, decayed, returned = KalmanModule.decay(
        [0.5, 0.5], [0.1, 0.2], last, now=NOW, decay_rate=0.01, max_uncertainty=1.0
    )

    assert decayed.tolist() == pytest.approx([0.2, 0.3])
    assert returned.tolist() == pytest.approx(decayed.tolist())


def test_decay_clamps_at_max_uncertainty():
    last = NOW - timedelta(hours=1000)
    _, decayed, _ = KalmanModule.decay(
        [0.5], [0.1], last, now=NOW, decay_rate=0.01, max_uncertainty=1.0
    )

    assert decayed.tolist() == [1.0]


def test_decay_is_deterministic():
    last = NOW - timedelta(hours=3)
    first = KalmanModule.decay([0.2], [0.3], last, now=NOW)
    second = KalmanModule.decay([0.2], [0.3], last, now=NOW)

    assert first[1].tolist() == second[1].tolist()


def test_apply_decays_then_reduces_uncertainty_toward_observation():
    last = NOW - timedelta(hours=10)
    position, uncertainty, decayed = KalmanModule.apply(
        [0.5],
        [0.1],
        [0.5],
        last_updated_at=last,
        now=NOW,
        weight=1.0,
        process_noise=0.1,
        measurement_noise=1.0,
    )

    assert decayed[0] == 0.2
    assert uncertainty[0] < decayed[0] + 0.1
    assert position[0] == 0.5


def test_update_without_mask_updates_every_dimension():
    position, uncertainty = KalmanModule.update(
        [0.0, 0.0],
        [1.0, 1.0],
        [1.0, 1.0],
        weight=0.3,
        process_noise=0.1,
        measurement_noise=1.0,
    )

    assert np.all(position > 0)
    assert np.all(uncertainty < 1.0)
