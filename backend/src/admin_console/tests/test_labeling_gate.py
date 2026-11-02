"""Pass 1 — table labeling runs unconditionally before schema extraction (FR-032..FR-035)."""

import pytest

from admin_console import services
from admin_console.models import SemanticLabel
from admin_console.tests.conftest import HOSTING_PLAN_VALUES

pytestmark = pytest.mark.django_db


def test_labeling_writes_semantic_labels(extracted_link, stub_domtrack):
    stub_domtrack.labels = {
        "tables": [
            {
                "columns": [
                    {"id": "col-0", "semantic_label": "فضای ذخیره‌سازی"},
                    {"id": "col-1", "semantic_label": "قیمت"},
                ]
            }
        ]
    }

    labels = services.label_link_tables(extracted_link)

    assert [entry["label"] for entry in labels] == ["فضای ذخیره‌سازی", "قیمت"]
    assert labels[0]["column_id"] == "col-0"
    assert SemanticLabel.objects.filter(label="فضای ذخیره‌سازی").exists()


def test_labeling_passes_the_domtrack_table_shape_to_the_labeler(
    extracted_link, stub_domtrack
):
    services.label_link_tables(extracted_link)

    sent = stub_domtrack.label_calls[0]
    assert sent and "meta" in sent[0] and "columns" in sent[0] and "rows" in sent[0]


def test_labels_feed_schema_extraction(extracted_link, stub_domtrack, stub_llm):
    stub_domtrack.labels = {
        "tables": [
            {
                "columns": [
                    {"id": "col-0", "semantic_label": "نام پلن"},
                    {"id": "col-1", "semantic_label": "قیمت"},
                ]
            }
        ]
    }
    services.label_link_tables(extracted_link)
    stub_llm.classifications = [
        {"table_index": 0, "is_correct": True, "plan_type": "hosting"}
    ]
    stub_llm.plans = [{"values": dict(HOSTING_PLAN_VALUES), "confidence": 1.0}]

    services.classify_and_extract_link_tables(extracted_link)

    context = stub_llm.plan_calls[0]["table"]
    assert context["columns"][:2] == ["نام پلن", "قیمت"]


def test_labeling_endpoint_labels_tables(
    operator_client, extracted_link, stub_domtrack
):
    stub_domtrack.labels = {
        "tables": [{"columns": [{"id": "col-0", "semantic_label": "قیمت"}]}]
    }

    response = operator_client.post(f"/api/v1/ops/links/{extracted_link.pk}/labeling")

    assert response.status_code == 200
    assert response.json()["labels"][0]["label"] == "قیمت"
