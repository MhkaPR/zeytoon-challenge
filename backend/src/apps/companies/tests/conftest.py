"""Shared pytest fixtures for the companies tests."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from accounts.models import ensure_role_groups
from companies import services
from companies.models import Company

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def role_groups(db):
    ensure_role_groups()


@pytest.fixture
def owner(db, role_groups):
    user = User.objects.create_user(
        username="+989120000001", phone_number="+989120000001", password="x"
    )
    user.groups.add(Group.objects.get(name=User.REGULAR_GROUP))
    return user


@pytest.fixture
def other_owner(db, role_groups):
    user = User.objects.create_user(
        username="+989120000002", phone_number="+989120000002", password="x"
    )
    user.groups.add(Group.objects.get(name=User.REGULAR_GROUP))
    return user


@pytest.fixture
def operator(db, role_groups):
    user = User.objects.create_user(
        username="+989120000003", phone_number="+989120000003", password="x"
    )
    user.groups.add(Group.objects.get(name=User.ADMIN_GROUP))
    return user


@pytest.fixture
def auth_client(api_client, owner):
    """An APIClient authenticated as ``owner`` via DRF force_authenticate is not used.

    The accounts JWT is resolved from the Authorization header, so we mint a real access
    token for the user.
    """
    from rest_framework_simplejwt.tokens import RefreshToken

    token = str(RefreshToken.for_user(owner).access_token)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client


@pytest.fixture
def company(owner):
    return services.register_company(
        owner,
        {
            "domain": "example.com",
            "company_name": "Example Hosting",
            "representative_name": "Ali Rezaei",
            "phone_number": "02123456789",
            "internal_number": "",
        },
    )
