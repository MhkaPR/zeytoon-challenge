import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from apps.recommendations.models import InterestProfile, InterestSignal
from apps.recommendations.services.v1.record import Interaction, RecordService


def _seed(visitor, positions, uncertainties=None, updated=None, counts=None):
    uncertainties = uncertainties or [[1.0] * len(row) for row in positions]
    InterestProfile.objects.create(
        visitor_id=visitor,
        position=[list(row) for row in positions],
        uncertainty=[list(row) for row in uncertainties],
        node_ids=[str(uuid.uuid4()) for _ in positions],
        node_updated_at=updated
        or [datetime.now(timezone.utc).isoformat()] * len(positions),
        node_signal_counts=counts or [0] * len(positions),
        activity_profile=[1.0] * len(positions),
    )


@pytest.mark.django_db
def test_single_node_moves_toward_interaction_via_kalman():
    visitor = uuid.uuid4()
    _seed(visitor, [[0.0, 0.0]])

    RecordService().record(
        visitor,
        Interaction(vector=[0.1, 0.1], weight=0.3, kind="details_view"),
    )

    profile = InterestProfile.objects.get(visitor_id=visitor)
    assert 0.0 < profile.position[0][0] < 0.1
    assert 0.0 < profile.position[0][1] < 0.1
    assert profile.node_signal_counts == [1]


@pytest.mark.django_db
def test_two_nodes_only_nearest_moves():
    visitor = uuid.uuid4()
    _seed(visitor, [[0.0, 0.0], [1.0, 1.0]])

    RecordService().record(
        visitor,
        Interaction(vector=[0.9, 0.9], weight=0.3, kind="details_view"),
    )

    profile = InterestProfile.objects.get(visitor_id=visitor)
    assert profile.position[0] == [0.0, 0.0]
    assert profile.position[1] != [1.0, 1.0]
    assert profile.node_signal_counts[0] == 0
    assert profile.node_signal_counts[1] == 1


@pytest.mark.django_db
def test_no_node_creates_one_at_interaction_vector():
    visitor = uuid.uuid4()

    RecordService().record(
        visitor,
        Interaction(vector=[0.3, 0.4], weight=0.3, kind="details_view"),
    )

    profile = InterestProfile.objects.get(visitor_id=visitor)
    assert len(profile.position) == 1
    assert profile.position[0] == pytest.approx([0.3, 0.4])
    assert profile.node_signal_counts == [1]


@pytest.mark.django_db
def test_far_interaction_updates_nearest_without_creating_a_node():
    visitor = uuid.uuid4()
    _seed(visitor, [[0.0, 0.0], [1.0, 1.0]])

    RecordService().record(
        visitor,
        Interaction(vector=[0.3, 0.3], weight=0.3, kind="details_view"),
    )

    profile = InterestProfile.objects.get(visitor_id=visitor)
    assert len(profile.position) == 2
    assert profile.position[0] != [0.0, 0.0]
    assert profile.position[1] == [1.0, 1.0]


@pytest.mark.django_db
def test_decay_increases_uncertainty_before_update():
    stale = uuid.uuid4()
    fresh = uuid.uuid4()
    ten_hours_ago = datetime.now(timezone.utc) - timedelta(hours=10)
    _seed(
        stale,
        [[0.5, 0.5]],
        uncertainties=[[0.1, 0.1]],
        updated=[ten_hours_ago.isoformat()],
    )
    _seed(fresh, [[0.5, 0.5]], uncertainties=[[0.1, 0.1]])

    RecordService().record(
        stale,
        Interaction(vector=[0.5, 0.5], weight=1.0, kind="details_view"),
    )
    RecordService().record(
        fresh,
        Interaction(vector=[0.5, 0.5], weight=1.0, kind="details_view"),
    )

    stale_profile = InterestProfile.objects.get(visitor_id=stale)
    fresh_profile = InterestProfile.objects.get(visitor_id=fresh)
    assert stale_profile.uncertainty[0][0] > fresh_profile.uncertainty[0][0]
    assert stale_profile.uncertainty[0][0] > 0.1


@pytest.mark.django_db
def test_same_interaction_id_is_idempotent():
    visitor = uuid.uuid4()
    _seed(visitor, [[0.0, 0.0]])
    service = RecordService()
    interaction = Interaction(
        vector=[0.1, 0.1],
        weight=0.3,
        kind="details_view",
        interaction_id="abc-123",
    )

    service.record(visitor, interaction)
    service.record(visitor, interaction)

    profile = InterestProfile.objects.get(visitor_id=visitor)
    assert profile.node_signal_counts == [1]
    assert InterestSignal.objects.filter(interaction_id="abc-123").count() == 1


def test_no_direct_state_arithmetic_outside_kalman():
    base = Path(__file__).resolve().parents[1] / "services" / "v1"
    forbidden = [
        r"position\s*\+=",
        r"uncertainty\s*\+=",
        r"self\.x\[",
        r"self\.s\[",
        r"\.x\[[^\]]*\]\s*=",
        r"\.s\[[^\]]*\]\s*=",
    ]
    for path in base.glob("*.py"):
        if path.name == "kalman.py":
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in forbidden:
            assert not re.search(pattern, text), f"{path.name} matches {pattern}"
