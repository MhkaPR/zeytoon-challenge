"""US9 — publishing through the catalog interface with provenance (FR-030, FR-036..FR-038)."""

import pytest

from apps.admin_console import services
from apps.admin_console.models import Link, PlanRecord
from apps.admin_console.tests.conftest import HOSTING_PLAN_VALUES
from apps.catalog.models import PublishedRecord

pytestmark = pytest.mark.django_db


def test_publish_writes_a_record_with_provenance(planned_link):
    published = services.publish_link_plans(planned_link)

    assert published == 1
    record = PublishedRecord.objects.get(
        source="admin_console", site=planned_link.site_id
    )
    assert record.link == planned_link.pk
    assert record.trace == planned_link.current_trace_id
    assert record.classification is not None
    assert record.plan_type == "hosting"
    assert record.values["plan_name"] == "Starter"
    assert record.is_published is True
    planned_link.refresh_from_db()
    assert planned_link.pipeline_stage == Link.PipelineStage.PUBLISHED


def test_publish_upserts_by_source_site_natural_key(planned_link, stub_llm):
    services.publish_link_plans(planned_link)
    updated = dict(HOSTING_PLAN_VALUES, price_amount=99000)
    stub_llm.plans = [{"values": updated, "confidence": 1.0}]
    services.extract_link_plans(planned_link)

    services.publish_link_plans(planned_link)

    records = PublishedRecord.objects.filter(
        source="admin_console", site=planned_link.site_id
    )
    assert records.count() == 1
    assert records.first().values["price_amount"] == 99000


def _classified_link(link):
    from apps.admin_console.models import TableClassification

    table = link.extracted_tables.get()
    if not TableClassification.objects.filter(table=table).exists():
        TableClassification.objects.create(
            table=table, is_plans_table=True, plan_type="hosting", confidence=0.9
        )
        table.refresh_from_db()
    return link


def test_incomplete_plan_is_not_published(labeled_link):
    labeled_link = _classified_link(labeled_link)
    table = labeled_link.extracted_tables.get()
    PlanRecord.objects.create(
        link=labeled_link,
        table=table,
        classification=table.classification,
        plan_type="hosting",
        natural_key="hosting:broken:0",
        values={"plan_name": "Broken"},  # required fields missing
        confidence=0.5,
    )

    with pytest.raises(ValueError, match="no_plan_records_met_quality_rules"):
        services.publish_link_plans(labeled_link)

    labeled_link.refresh_from_db()
    assert labeled_link.pipeline_stage == Link.PipelineStage.EXTRACTED
    assert PublishedRecord.objects.count() == 0


def test_removal_retires_the_published_record(planned_link):
    services.publish_link_plans(planned_link)

    retired = services.retire_missing_plans(planned_link, current_keys=set())

    assert retired == 1
    record = PublishedRecord.objects.get(
        source="admin_console", site=planned_link.site_id
    )
    assert record.is_published is False
    assert record.retired_at is not None


def test_kept_plan_is_not_retired(planned_link):
    services.publish_link_plans(planned_link)
    keys = set(planned_link.plan_records.values_list("natural_key", flat=True))

    retired = services.retire_missing_plans(planned_link, current_keys=keys)

    assert retired == 0
    assert (
        PublishedRecord.objects.get(
            source="admin_console", site=planned_link.site_id
        ).is_published
        is True
    )


def test_ignored_plan_is_retired_and_stays_excluded_after_reextraction(
    planned_link, stub_llm
):
    services.publish_link_plans(planned_link)
    record = PlanRecord.objects.get(link=planned_link)
    services.set_plan_excluded(planned_link, record, True)

    published = PublishedRecord.objects.get(
        source="admin_console", site=planned_link.site_id
    )
    assert published.is_published is False

    stub_llm.plans = [{"values": dict(HOSTING_PLAN_VALUES), "confidence": 1.0}]
    services.extract_link_plans(planned_link)
    assert services.publish_link_plans(planned_link) == 0
    assert services.unignored_plan_keys(planned_link) == set()
