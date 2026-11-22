"""SMS gateway adapter.

The domain depends only on the ``SmsGateway`` interface. The concrete implementation is
selected from the environment (``SMS_GATEWAY_BACKEND``); tests use the console/fake gateway.
"""

import httpx
import logging

from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


class SmsGateway:
    """Interface every SMS gateway implementation must satisfy."""

    def send_code(self, phone_number, code):
        raise NotImplementedError


class ConsoleSmsGateway(SmsGateway):
    """Development/test gateway that logs the code instead of sending an SMS.

    The masking filter keeps the code out of production logs; this gateway is only used when
    explicitly configured for local development or tests.
    """

    def send_code(self, phone_number, code):
        extra = {"event": "sms_console_send"}
        print(f"message of console for sms: {code}")
        logger.info(
            "sms.console_send",
            extra=extra,
        )
        return True


class CapturingSmsGateway(SmsGateway):
    """Test gateway that records the last code sent per phone number."""

    sent = {}

    def send_code(self, phone_number, code):
        type(self).sent[phone_number] = code
        return True

    @classmethod
    def last_code(cls, phone_number):
        return cls.sent.get(phone_number)


class PayamakPanelSmsGateway(SmsGateway):
    """Send OTP codes through the Melipayamak shared-template API."""

    def __init__(self):
        self.body_id = settings.SMS_GATEWAY_BODY_ID
        self.token = settings.SMS_GATEWAY_TOKEN
        self.base_url = settings.SMS_GATEWAY_BASE_URL.rstrip("/")

    def send_code(self, phone_number, code):
        if not self.token:
            raise RuntimeError("SMS_GATEWAY_TOKEN is not configured")
        if not self.body_id:
            raise RuntimeError("SMS_GATEWAY_BODY_ID is not configured")

        response = httpx.post(
            f"{self.base_url}/api/send/shared/{self.token}",
            json={
                "bodyId": self.body_id,
                "to": phone_number,
                "args": [str(code)],
            },
            timeout=10.0,
        )
        response.raise_for_status()
        result = response.json()
        if isinstance(result, dict) and result.get("status") in {"error", "failed", False}:
            raise RuntimeError("Melipayamak rejected the SMS request")
        return True


# Backwards-compatible name for existing deployments selecting this class.
HttpSmsGateway = PayamakPanelSmsGateway


def get_gateway():
    """Return the configured SMS gateway instance."""
    return import_string(settings.SMS_GATEWAY_BACKEND)()
