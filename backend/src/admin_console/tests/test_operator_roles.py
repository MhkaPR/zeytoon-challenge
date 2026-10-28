"""Role separation: the ``ops`` group works in the console; ``admin`` adds Django admin."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

pytestmark = pytest.mark.django_db

User = get_user_model()


def _client_for(user):
    client = APIClient()
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


def test_ops_group_member_can_read_the_console(role_groups):
    user = User.objects.create_user(
        username="+989120000201", phone_number="+989120000201", password="x"
    )
    user.groups.add(Group.objects.get(name=User.OPS_GROUP))

    response = _client_for(user).get("/api/v1/ops/approvals")

    assert response.status_code == 200


def test_ops_group_member_is_not_staff(role_groups):
    user = User.objects.create_user(
        username="+989120000202", phone_number="+989120000202", password="x"
    )
    user.groups.add(Group.objects.get(name=User.OPS_GROUP))

    assert user.role() == "ops"
    assert user.is_staff is False


def test_regular_user_is_still_refused(role_groups):
    user = User.objects.create_user(
        username="+989120000203", phone_number="+989120000203", password="x"
    )
    user.groups.add(Group.objects.get(name=User.REGULAR_GROUP))

    response = _client_for(user).get("/api/v1/ops/approvals")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "admin_required"
