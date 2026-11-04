"""Domain-event logging regression tests (FR-046)."""

import json
import logging

import pytest

from apps.companies import events
from apps.companies.services import (
    record_credit_movement,
    record_verification_decision,
    register_company,
)
from apps.utils.logging import JsonFormatter, SensitiveDataFilter

pytestmark = pytest.mark.django_db

FULL_PHONE = "02123456789"


class _Capture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(self.format(record))


@pytest.fixture
def captured_logs():
    handler = _Capture()
    handler.addFilter(SensitiveDataFilter())
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("companies")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    yield handler
    logger.removeHandler(handler)


def _register(owner):
    return register_company(
        owner,
        {
            "domain": "example.com",
            "company_name": "Example Hosting",
            "representative_name": "Ali Rezaei",
            "phone_number": FULL_PHONE,
        },
    )


def test_events_log_the_phone_without_masking(owner, operator, captured_logs):
    company = _register(owner)
    record_verification_decision(company, operator, "approved")
    record_credit_movement(company, "charge", 100, "payment")
    events.ownership_transfer_refused(company, actor=owner)

    joined = "\n".join(captured_logs.records)
    assert captured_logs.records, "expected some structured events"
    assert FULL_PHONE in joined
    # Every record is valid JSON.
    for line in captured_logs.records:
        json.loads(line)
