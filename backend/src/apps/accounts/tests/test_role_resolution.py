"""Domain test: role resolution across guest, regular, and admin (spec FR-009)."""

import pytest

from apps.accounts import selectors
from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def test_role_of_none_is_guest():
    assert selectors.get_user_role(None) == "guest"


def test_regular_user_role(regular_user):
    assert selectors.get_user_role(regular_user) == "regular"


def test_admin_user_role(admin_user):
    assert selectors.get_user_role(admin_user) == "admin"


def test_admin_wins_over_regular(role_groups):
    from django.contrib.auth.models import Group

    user = User.objects.create_user(
        username="+989120000001", phone_number="+989120000001", password="x"
    )
    user.groups.add(Group.objects.get(name=User.REGULAR_GROUP))
    user.groups.add(Group.objects.get(name=User.ADMIN_GROUP))
    assert user.role() == "admin"


def test_ops_group_is_an_operator_but_not_an_admin(role_groups):
    from django.contrib.auth.models import Group

    user = User.objects.create_user(
        username="+989120000002", phone_number="+989120000002", password="x"
    )
    user.groups.add(Group.objects.get(name=User.OPS_GROUP))

    assert user.role() == "ops"
    assert user.is_operator() is True
    assert user.is_admin() is False


def test_admin_wins_over_ops(role_groups):
    from django.contrib.auth.models import Group

    user = User.objects.create_user(
        username="+989120000003", phone_number="+989120000003", password="x"
    )
    user.groups.add(Group.objects.get(name=User.OPS_GROUP))
    user.groups.add(Group.objects.get(name=User.ADMIN_GROUP))

    assert user.role() == "admin"
