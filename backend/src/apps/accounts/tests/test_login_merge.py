import pytest
from django.test import TestCase

from apps.accounts.models import User
from apps.accounts.services import verify_otp
from apps.recommendations.models import InterestProfile


class LoginMergeTests(TestCase):
    def test_verify_merges_device_history_into_fresh_account(self):
        from apps.accounts import state

        visitor = "44444444-4444-4444-4444-444444444444"
        profile = InterestProfile.objects.create(
            visitor_id=visitor,
            position=[0.5],
            uncertainty=[0.5],
            space_version="v1",
            signal_count=2,
        )
        code = "123456"
        state.store_code("09120000009", code)

        result = verify_otp("09120000009", code, visitor_id=visitor)

        profile.refresh_from_db()
        account = InterestProfile.objects.get(user=result["user"])
        assert account.position == [0.5]
        assert profile.merged_into_id == result["user"].pk
