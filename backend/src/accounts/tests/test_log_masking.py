"""Security test: logs never contain full phone numbers, codes, or tokens (FR-026)."""

import logging

import pytest

from accounts import services
from utils.logging import JsonFormatter, SensitiveDataFilter, mask_phone, mask_text

pytestmark = pytest.mark.django_db

PHONE = "+989123456789"


def test_mask_phone_keeps_only_prefix_and_suffix():
    masked = mask_phone(PHONE)
    assert PHONE not in masked
    # Rendered in national format so the owner still recognizes it, but never the full value.
    assert masked == "0912***6789"


def test_mask_text_redacts_phone_code_and_token():
    text = f"phone={PHONE} code=123456 token=abc.def.ghi"
    masked = mask_text(text)
    assert PHONE not in masked
    assert "123456" not in masked
    assert "abc.def.ghi" not in masked


def test_filter_masks_record_message_and_args():
    record = logging.LogRecord(
        "t", logging.INFO, __file__, 1, "otp for %s", (PHONE,), None
    )
    SensitiveDataFilter().filter(record)
    rendered = JsonFormatter().format(record)
    assert PHONE not in rendered


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


def test_otp_flow_logs_do_not_leak_phone(issued_code, caplog):
    code = issued_code(PHONE)
    with caplog.at_level(logging.INFO):
        services.verify_otp(PHONE, code)
    assert caplog.records, "expected log records"
    for record in caplog.records:
        # The service logs a masked identifier in ``extra`` and never the raw phone.
        phone = getattr(record, "phone", None)
        if phone is not None:
            assert PHONE not in phone
        assert PHONE not in record.getMessage()
