"""Log-masking guard (FR-044, SC-018).

No console log record may carry an unmasked phone number or trace content.
"""

import logging

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from apps.accounts.models import ensure_role_groups
from apps.admin_console import events
from apps.pipeline.models import Site

User = get_user_model()

PHONE = "+989120000301"
REPRESENTATIVE_PHONE = "02123456789"


@pytest.mark.django_db
def test_events_never_log_the_unmasked_phone(caplog):
    ensure_role_groups()
    user = User.objects.create_user(username=PHONE, phone_number=PHONE, password="x")
    user.groups.add(Group.objects.get(name=User.ADMIN_GROUP))
    from apps.companies import services as company_services

    company = company_services.register_company(
        user,
        {
            "domain": "mask.example.com",
            "company_name": "Mask Co",
            "representative_name": "Rep",
            "phone_number": REPRESENTATIVE_PHONE,
        },
    )
    site = Site.objects.create(company=company, domain=company.domain)

    with caplog.at_level(logging.INFO, logger="admin_console.events"):
        events.site_onboarded(site, actor=user)

    for record in caplog.records:
        message = record.getMessage()
        assert PHONE not in message
        assert REPRESENTATIVE_PHONE not in message


@pytest.mark.django_db
def test_trace_content_is_never_logged(caplog, traced_link, operator_client):
    with caplog.at_level(logging.INFO, logger="admin_console.events"):
        operator_client.post(f"/api/v1/ops/links/{traced_link.pk}/extractions")
    blob = "Plan 0"  # text that lives only inside the trace body
    for record in caplog.records:
        assert blob not in record.getMessage()
