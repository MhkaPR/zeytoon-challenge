"""Shared pytest fixtures for the accounts tests."""

import pytest
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

from apps.accounts import state
from apps.accounts.models import User, ensure_role_groups
from apps.accounts.sms import CapturingSmsGateway


@pytest.fixture(autouse=True)
def _use_test_sms_gateway(settings):
    settings.SMS_GATEWAY_BACKEND = "accounts.sms.CapturingSmsGateway"
    CapturingSmsGateway.sent = {}
    yield


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def role_groups(db):
    ensure_role_groups()


@pytest.fixture
def regular_user(db, role_groups):
    from django.contrib.auth.models import Group

    user = User.objects.create_user(
        username="+989123456789", phone_number="+989123456789", password="x"
    )
    user.groups.add(Group.objects.get(name=User.REGULAR_GROUP))
    return user


@pytest.fixture
def admin_user(db, role_groups):
    from django.contrib.auth.models import Group

    user = User.objects.create_user(
        username="+989999999999", phone_number="+989999999999", password="x"
    )
    user.groups.add(Group.objects.get(name=User.ADMIN_GROUP))
    return user


@pytest.fixture
def issued_code(db):
    """Return a helper that issues a code for a phone and returns the plaintext code."""

    def _issue(phone_number):
        code = state.generate_code()
        state.store_code(phone_number, code)
        return code

    return _issue
