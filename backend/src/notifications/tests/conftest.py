"""Fixtures for the notifications tests: an operator and a plain user."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from rest_framework.test import APIClient

from accounts.models import ensure_role_groups

User = get_user_model()


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    """Keep DRF throttle counters out of the shared Redis cache between tests."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def role_groups(db):
    ensure_role_groups()


@pytest.fixture
def operator(db, role_groups):
    user = User.objects.create_user(
        username="+989120000201", phone_number="+989120000201", password="x"
    )
    user.groups.add(Group.objects.get(name=User.ADMIN_GROUP))
    return user


@pytest.fixture
def other_user(db, role_groups):
    user = User.objects.create_user(
        username="+989120000202", phone_number="+989120000202", password="x"
    )
    user.groups.add(Group.objects.get(name=User.REGULAR_GROUP))
    return user


def _auth(user):
    """Return a fresh authenticated client so two fixtures never share credentials."""
    from rest_framework_simplejwt.tokens import RefreshToken

    client = APIClient()
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.fixture
def operator_client(operator):
    return _auth(operator)


@pytest.fixture
def user_client(other_user):
    return _auth(other_user)
