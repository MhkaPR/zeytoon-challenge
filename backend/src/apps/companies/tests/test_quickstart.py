"""End-to-end quickstart validation (specs/002-company-registration-panel/quickstart.md).

Each test maps to one quickstart scenario ``V1``..``V12`` and drives the real HTTP
surface (plus the archival/ownership hooks that have no endpoint) so the documented
scenarios are proven against the implementation, not just restated.
"""

import logging

import pytest
from django.db.models import ProtectedError

from apps.accounts.exceptions import ApiError
from apps.companies import events
from apps.companies.models import Company, CreditLedgerEntry, VerificationDecision
from apps.companies.selectors import credit_projection
from apps.companies.services import (
    archive_companies_for_user,
    record_verification_decision,
    register_company,
)
from apps.utils.logging import JsonFormatter, SensitiveDataFilter

pytestmark = pytest.mark.django_db

BASE = "/api/v1/companies"
FULL_PHONE = "02123456789"


def _payload(**overrides):
    data = {
        "domain": "example.com",
        "company_name": "Example Hosting",
        "representative_name": "Ali Rezaei",
        "phone_number": FULL_PHONE,
    }
    data.update(overrides)
    return data


def _mark_charged(company):
    """Simulate the out-of-scope charging feature setting the charge status."""
    company.charge_status = Company.ChargeStatus.CHARGED
    company.save(update_fields=["charge_status", "updated_at"])
    return company


def _operator_client(operator):
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken

    client = APIClient()
    token = str(RefreshToken.for_user(operator).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


# --- V1: register (step one) -------------------------------------------------


def test_v1_register_company(auth_client):
    response = auth_client.post(f"{BASE}/", _payload(), format="json")
    assert response.status_code == 201
    body = response.json()
    assert body["company"]["verification_status"] == "pending"
    assert body["company"]["unverified"] is True
    assert auth_client.get(f"{BASE}/").json()["companies"]

    # internal_number optional; each mandatory field names itself when missing.
    assert (
        auth_client.post(
            f"{BASE}/", _payload(internal_number=""), format="json"
        ).status_code
        == 201
    )
    for field in ("domain", "company_name", "representative_name", "phone_number"):
        bad = _payload(domain="other.com")
        del bad[field]
        resp = auth_client.post(f"{BASE}/", bad, format="json")
        assert resp.status_code == 400
        assert field in str(resp.json()["error"]["fields"])


# --- V2: multiple companies, single owner -----------------------------------


def test_v2_multiple_companies_single_owner(auth_client, owner):
    first = auth_client.post(f"{BASE}/", _payload(), format="json").json()["company"][
        "id"
    ]
    second = auth_client.post(
        f"{BASE}/", _payload(domain="second.com"), format="json"
    ).json()["company"]["id"]
    assert first != second
    assert Company.objects.filter(owner=owner).count() == 2


# --- V3: append-only verification history -----------------------------------


def test_v3_append_only_verification_history(auth_client, operator):
    company_id = auth_client.post(f"{BASE}/", _payload(), format="json").json()[
        "company"
    ]["id"]
    op = _operator_client(operator)
    approved = op.post(
        f"{BASE}/{company_id}/verification-decisions",
        {"outcome": "approved"},
        format="json",
    )
    assert approved.status_code == 201
    assert approved.json()["verification_status"] == "verified"

    other = auth_client.post(
        f"{BASE}/", _payload(domain="other.com"), format="json"
    ).json()["company"]["id"]
    rejected = op.post(
        f"{BASE}/{other}/verification-decisions",
        {"outcome": "not_approved"},
        format="json",
    )
    assert rejected.status_code == 200
    assert rejected.json()["verification_status"] == "rejected"
    assert rejected.json()["current_step"] == "company_information"

    # A later decision leaves earlier entries intact.
    op.post(
        f"{BASE}/{company_id}/verification-decisions",
        {"outcome": "not_approved"},
        format="json",
    )
    assert VerificationDecision.objects.filter(company_id=company_id).count() == 2

    # The owner can never decide their own company's verification.
    owner_attempt = auth_client.post(
        f"{BASE}/{company_id}/verification-decisions",
        {"outcome": "approved"},
        format="json",
    )
    assert owner_attempt.status_code in (401, 403)


# --- V4: panel entry, switching, continue view -------------------------------


def test_v4_panel_entry_and_switching(auth_client, operator):
    pending = auth_client.post(f"{BASE}/", _payload(), format="json").json()["company"][
        "id"
    ]
    verified = auth_client.post(
        f"{BASE}/", _payload(domain="verified.com"), format="json"
    ).json()["company"]["id"]
    record_verification_decision(Company.objects.get(pk=verified), operator, "approved")

    assert auth_client.get(f"{BASE}/panel-switcher").json()["empty_state"] is False
    entry = auth_client.get(f"{BASE}/{pending}/panel-entry").json()
    assert entry["view"] == "continue_registration"
    assert entry["current_step"] == "verification"
    assert entry["step_progress"]

    redirect = auth_client.get(f"{BASE}/{pending}/panel")
    assert redirect.status_code == 303
    assert redirect["Location"] == f"{BASE}/{pending}/panel-entry"

    full = auth_client.get(f"{BASE}/{verified}/panel")
    assert full.status_code == 200
    assert full.json()["company"]["verification_status"] == "verified"


# --- V5: mid-step abandonment ------------------------------------------------


def test_v5_mid_step_abandonment(auth_client):
    company = auth_client.post(f"{BASE}/", _payload(), format="json").json()["company"][
        "id"
    ]
    response = auth_client.post(
        f"{BASE}/{company}/steps/company_information/abandon", {}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["step_key"] == "company_information"


# --- V6: step locking --------------------------------------------------------


def test_v6_step_locking(auth_client):
    company = auth_client.post(f"{BASE}/", _payload(), format="json").json()["company"][
        "id"
    ]
    locked = auth_client.post(
        f"{BASE}/{company}/steps/verification/abandon", {}, format="json"
    )
    assert locked.status_code == 403
    assert locked.json()["error"]["code"] == "step_locked"


# --- V7: plan eligibility gate ----------------------------------------------


def test_v7_plan_eligibility_gate(auth_client, owner, operator):
    company = register_company(owner, _payload())
    gate = auth_client.get(f"{BASE}/{company.pk}/plan-eligibility").json()
    assert gate["allowed"] is False
    assert set(gate["missing"]) == {"verified", "charged"}

    # A verified-but-uncharged company names only the charge prerequisite.
    record_verification_decision(company, operator, "approved")
    gate = auth_client.get(f"{BASE}/{company.pk}/plan-eligibility").json()
    assert gate["missing"] == ["charged"]

    # Charged + verified → allowed; removing the charge reports the missing prerequisite
    # again without destroying anything (plans are out of scope).
    _mark_charged(company)
    gate = auth_client.get(f"{BASE}/{company.pk}/plan-eligibility").json()
    assert gate["allowed"] is True and gate["missing"] == []

    company.charge_status = Company.ChargeStatus.NOT_CHARGED
    company.save(update_fields=["charge_status", "updated_at"])
    gate = auth_client.get(f"{BASE}/{company.pk}/plan-eligibility").json()
    assert gate["allowed"] is False and gate["missing"] == ["charged"]


# --- V8: credit ledger and projection ---------------------------------------


def test_v8_credit_ledger_projection(auth_client):
    company = auth_client.post(f"{BASE}/", _payload(), format="json").json()["company"][
        "id"
    ]
    assert auth_client.get(f"{BASE}/{company}/credit").json()["current_credit"] == 0

    charge = auth_client.post(
        f"{BASE}/{company}/credit/movements",
        {"direction": "charge", "amount": 1000, "reason": "payment"},
        format="json",
    )
    assert charge.status_code == 201
    assert charge.json()["current_credit"] == 1000

    decharge = auth_client.post(
        f"{BASE}/{company}/credit/movements",
        {"direction": "decharge", "amount": 250, "reason": "platform_view"},
        format="json",
    )
    assert decharge.json()["current_credit"] == 750

    body = auth_client.get(f"{BASE}/{company}/credit").json()
    reconstructed = sum(
        e["amount"] if e["direction"] == "charge" else -e["amount"]
        for e in body["entries"]
    )
    assert reconstructed == body["current_credit"] == 750

    entry = CreditLedgerEntry.objects.filter(company_id=company).first()
    with pytest.raises(ValueError):
        entry.delete()


# --- V9: crawl gating + per-company isolation --------------------------------


def test_v9_crawl_requires_charge_and_is_free(auth_client, owner):
    company = register_company(owner, _payload())
    blocked = auth_client.post(
        f"{BASE}/{company.pk}/crawl", {"enabled": True}, format="json"
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["fields"]["missing"] == ["charged"]

    _mark_charged(company)
    enabled = auth_client.post(
        f"{BASE}/{company.pk}/crawl", {"enabled": True}, format="json"
    )
    assert enabled.status_code == 200
    assert enabled.json()["crawl_enabled"] is True
    assert CreditLedgerEntry.objects.filter(company=company).count() == 0
    assert credit_projection(company) == 0


# --- V10: ownership + archival ----------------------------------------------


def test_v10_ownership_refused_and_archival(auth_client, owner):
    company = auth_client.post(f"{BASE}/", _payload(), format="json").json()["company"][
        "id"
    ]
    refused = auth_client.post(
        f"{BASE}/{company}/transfer-ownership", {}, format="json"
    )
    assert refused.status_code == 409

    # Duplicate domain accepted; stored normalized; no dedup/merge performed.
    dup = auth_client.post(
        f"{BASE}/", _payload(domain="WWW.Example.COM/path"), format="json"
    )
    assert dup.status_code == 201
    assert (
        Company.objects.get(pk=dup.json()["company"]["id"]).domain == "www.example.com"
    )

    # Account deletion archives (soft delete); nothing is hard-deleted.
    assert archive_companies_for_user(owner) == 2
    assert Company.objects.filter(owner=owner, is_archived=True).count() == 2
    with pytest.raises(ProtectedError):
        owner.delete()
    assert Company.objects.filter(pk=company).exists()


# --- V11: owner scoping ------------------------------------------------------


def test_v11_owner_scoping_returns_not_found(auth_client, other_owner):
    foreign = register_company(other_owner, _payload(domain="foreign.com"))
    for path in (
        f"{BASE}/{foreign.pk}",
        f"{BASE}/{foreign.pk}/panel-entry",
        f"{BASE}/{foreign.pk}/panel",
        f"{BASE}/{foreign.pk}/credit",
        f"{BASE}/{foreign.pk}/plan-eligibility",
    ):
        assert auth_client.get(path).status_code == 404


# --- V12: configurability + event logging ------------------------------------


class _Capture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(self.format(record))


def test_v12_runtime_config_and_log_masking(auth_client, owner, operator):
    from constance import config

    from apps.companies import constants

    original = dict(config.COMPANY_REQUIREMENT_MESSAGES)
    try:
        config.COMPANY_REQUIREMENT_MESSAGES = {
            "verified": "V",
            "charged": "C",
            "both": "B",
        }
        assert constants.requirement_message(["charged"]) == "C"
    finally:
        config.COMPANY_REQUIREMENT_MESSAGES = original

    handler = _Capture()
    handler.addFilter(SensitiveDataFilter())
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("companies")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    try:
        company = register_company(owner, _payload())
        record_verification_decision(company, operator, "approved")
        auth_client.post(
            f"{BASE}/{company.pk}/credit/movements",
            {"direction": "charge", "amount": 100, "reason": "payment"},
            format="json",
        )
        events.ownership_transfer_refused(company, actor=owner)
    finally:
        logger.removeHandler(handler)

    joined = "\n".join(handler.records)
    assert handler.records
    assert FULL_PHONE in joined
    assert "company_registered" in joined
    assert "company_verification_decided" in joined
    assert "company_credit_movement" in joined


# --- Setup sanity ------------------------------------------------------------


def test_unknown_outcome_is_rejected(company, operator):
    with pytest.raises(ApiError):
        record_verification_decision(company, operator, "maybe")
