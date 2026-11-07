import pytest

from apps.accounts.models import User
from apps.recommendations.models import InterestProfile
from apps.recommendations.services.v1.merging import StateMerger


@pytest.mark.django_db
def test_device_history_moves_to_empty_account():
    user = User.objects.create_user(username="u", password="x", phone_number="09120000002")
    visitor = InterestProfile.objects.create(
        visitor_id="11111111-1111-1111-1111-111111111111",
        position=[0.2, 0.8],
        uncertainty=[0.5, 0.5],
        space_version="v1",
        signal_count=3,
    )
    account = StateMerger.merge_on_login(user, visitor.visitor_id)
    visitor.refresh_from_db()
    assert account.position == [0.2, 0.8]
    assert visitor.merged_into_id == user.pk


@pytest.mark.django_db
def test_account_history_wins_when_both_exist():
    user = User.objects.create_user(username="u", password="x", phone_number="09120000003")
    InterestProfile.objects.create(
        user=user, position=[0.9], uncertainty=[0.1], space_version="v1"
    )
    visitor = InterestProfile.objects.create(
        visitor_id="22222222-2222-2222-2222-222222222222",
        position=[0.1],
        uncertainty=[0.9],
        space_version="v1",
    )
    account = StateMerger.merge_on_login(user, visitor.visitor_id)
    assert account.position == [0.9]


@pytest.mark.django_db
def test_clear_visitor_removes_device_profile():
    visitor = InterestProfile.objects.create(
        visitor_id="33333333-3333-3333-3333-333333333333"
    )
    StateMerger.clear_visitor(visitor.visitor_id)
    assert not InterestProfile.objects.filter(visitor_id=visitor.visitor_id).exists()
