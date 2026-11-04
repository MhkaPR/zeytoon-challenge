"""SMS gateway adapter.

The domain depends only on the ``SmsGateway`` interface. The concrete implementation is
selected from the environment (``SMS_GATEWAY_BACKEND``); tests use the console/fake gateway.
"""

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


class HttpSmsGateway(SmsGateway):
    """Placeholder HTTP gateway reading credentials from the environment."""

    def __init__(self):
        self.api_key = settings.SMS_GATEWAY_API_KEY
        self.sender = settings.SMS_GATEWAY_SENDER
        self.base_url = settings.SMS_GATEWAY_BASE_URL

    def send_code(self, phone_number, code):
        # A real integration would POST to ``self.base_url`` with the credentials above.
        if not self.api_key:
            raise RuntimeError("SMS_GATEWAY_API_KEY is not configured")
        raise NotImplementedError("Configure a concrete SMS gateway implementation.")


def get_gateway():
    """Return the configured SMS gateway instance."""
    return import_string(settings.SMS_GATEWAY_BACKEND)()
