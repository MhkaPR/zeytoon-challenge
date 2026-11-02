"""Regression tests for bugs fixed during implementation (constitution Principle VIII).

Each test names the bug it guards against so it is clear why it exists.
"""

import pytest
from constance.test import override_config

from accounts import services
from accounts.models import User

pytestmark = pytest.mark.django_db


@override_config(RETURN_URL_ALLOWLIST=["/", "/plans"], DEFAULT_RETURN_PATH="/")
def test_regression_root_allowlist_does_not_match_every_path():
    """Bug: the root entry ``/`` in the allowlist matched any path via a prefix check.

    ``/admin/secret`` must NOT be considered allowlisted just because ``/`` is allowed.
    """
    assert services.resolve_return_url("/admin/secret") == "/"
    assert services.resolve_return_url("/plans") == "/plans"


@override_config(RETURN_URL_ALLOWLIST=["/", "/plans"], DEFAULT_RETURN_PATH="/")
def test_regression_protocol_relative_url_is_rejected():
    """Bug: protocol-relative URLs (``//host``) were not treated as absolute."""
    assert services.resolve_return_url("//evil.example.com/path") == "/"


def test_regression_superuser_is_an_admin(role_groups):
    """Bug: ``createsuperuser`` produced an account whose ``role()`` was ``regular``.

    A Django superuser is expected to be a full operator, so it must resolve to the admin
    role even though it is not a member of the ``admin`` group.
    """
    user = User.objects.create_superuser(
        username="+989000000000", phone_number="+989000000000", password="x"
    )
    assert user.role() == User.ADMIN_GROUP
    assert user.is_admin()
