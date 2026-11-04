"""Security test: logs never contain one-time codes or tokens; phones are unmasked."""

import logging

import pytest

from apps.accounts import services
from apps.utils.logging import JsonFormatter, SensitiveDataFilter, mask_text

pytestmark = pytest.mark.django_db

PHONE = "+989123456789"


def test_mask_text_redacts_code_and_token_but_keeps_phone():
    text = f"phone={PHONE} code=424242 token=abc.def.ghi"
    masked = mask_text(text)
    assert PHONE in masked
    assert "424242" not in masked
    assert "abc.def.ghi" not in masked


def test_filter_redacts_secrets_in_record_message_and_args():
    record = logging.LogRecord(
        "t", logging.INFO, __file__, 1, "code=%s token=%s", ("123456", "abc.def.ghi"), None
    )
    SensitiveDataFilter().filter(record)
    rendered = JsonFormatter().format(record)
    assert "123456" not in rendered
    assert "abc.def.ghi" not in rendered


def test_filter_preserves_numeric_format_arguments():
    record = logging.LogRecord(
        "httpx",
        logging.INFO,
        __file__,
        1,
        'HTTP %s "%s %d %s"',
        ("GET", "https://example.com", 200, "OK"),
        None,
    )

    SensitiveDataFilter().filter(record)

    assert record.getMessage() == 'HTTP GET "https://example.com 200 OK"'


def test_otp_flow_logs_the_phone_without_masking(issued_code, caplog):
    code = issued_code(PHONE)
    with caplog.at_level(logging.INFO):
        services.verify_otp(PHONE, code)
    assert caplog.records, "expected log records"
    logged_phones = [getattr(record, "phone", None) for record in caplog.records]
    assert PHONE in logged_phones
