"""LLM cost-ceiling tests (US5, Principle II, FR-024)."""

from unittest.mock import patch

import pytest
from constance.test import override_config

from admin_console.models import LlmCostLedger, SemanticLabel
from admin_console.services import (
    extract_tables_for_link,
    label_tables_for_link,
    set_llm_ceiling,
)
from notifications.models import Notification

pytestmark = pytest.mark.django_db


@override_config(LABELING_ENABLED=True)
def test_ceiling_exceeded_stops_and_writes_nothing(traced_link, operator):
    extract_tables_for_link(traced_link)
    set_llm_ceiling(0.001, period="monthly", actor=operator)
    with patch("admin_console.domtrack_client.label_tables") as mock_label:
        with pytest.raises(Exception) as exc:
            label_tables_for_link(traced_link, estimated_cost=0.01)
    assert getattr(exc.value, "code", None) == "llm_ceiling_exceeded"
    mock_label.assert_not_called()
    assert SemanticLabel.objects.count() == 0
    assert not LlmCostLedger.objects.filter(amount__isnull=False).exists()
    assert Notification.objects.filter(event_type="llm_ceiling_exceeded").count() == 1


@override_config(LABELING_ENABLED=True)
def test_ceiling_endpoint_requires_admin(auth_client):
    response = auth_client.get("/api/v1/ops/llm-cost-ceiling")
    assert response.status_code == 403


def test_ceiling_endpoint_admin_round_trip(operator_client):
    response = operator_client.put(
        "/api/v1/ops/llm-cost-ceiling",
        {"ceiling_amount": 25.0, "period": "monthly"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["ceiling"] == 25.0
    assert response.json()["exceeded"] is False
