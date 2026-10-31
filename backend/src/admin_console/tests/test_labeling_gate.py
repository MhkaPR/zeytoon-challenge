"""US8 — labeling is optional, admin-gated, and never blocks the pipeline (FR-032..FR-035)."""

import pytest
from constance import config

from admin_console import services
from admin_console.models import SemanticLabel

pytestmark = pytest.mark.django_db


@pytest.fixture
def labeling_enabled():
    previous = config.LABELING_ENABLED
    config.LABELING_ENABLED = True
    yield
    config.LABELING_ENABLED = previous


def test_labeling_is_disabled_by_default(extracted_link):
    assert config.LABELING_ENABLED is False
    with pytest.raises(PermissionError, match="labeling_disabled"):
        services.label_link_tables(extracted_link)
    assert SemanticLabel.objects.count() == 0


def test_disabled_labeling_endpoint_returns_403(operator_client, extracted_link):
    response = operator_client.post(f"/api/v1/ops/links/{extracted_link.pk}/labeling")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "labeling_disabled"


def test_enabled_labeling_writes_labels_without_touching_the_pipeline(
    extracted_link, stub_domtrack, labeling_enabled
):
    stage_before = extracted_link.pipeline_stage
    stub_domtrack.labels = {
        "tables": [{"columns": [{"id": "col-0", "label": "فضای ذخیره‌سازی"}]}]
    }

    labels = services.label_link_tables(extracted_link)

    assert len(labels) == 1
    assert labels[0]["column_id"] == "col-0"
    assert labels[0]["label"] == "فضای ذخیره‌سازی"
    assert SemanticLabel.objects.filter(label="فضای ذخیره‌سازی").exists()
    extracted_link.refresh_from_db()
    assert extracted_link.pipeline_stage == stage_before
