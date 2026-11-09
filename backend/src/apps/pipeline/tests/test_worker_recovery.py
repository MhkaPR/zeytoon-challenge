from types import SimpleNamespace

import pytest
from django.utils import timezone

from apps.pipeline import tasks
from apps.pipeline.services.v1 import pipeline as services
from apps.pipeline.models import Link, PlanRecord

pytestmark = pytest.mark.django_db


def test_worker_startup_queues_clean_unfinished_sites_only(site, monkeypatch):
    clean_link = Link.objects.create(
        site=site,
        url="https://example.com/clean",
        url_hash="clean-link",
        review_state=Link.ReviewState.KEPT,
        pipeline_stage=Link.PipelineStage.CAPTURED,
    )
    Link.objects.create(
        site=site,
        url="https://example.com/parked",
        url_hash="parked-link",
        review_state=Link.ReviewState.KEPT,
        pipeline_stage=Link.PipelineStage.EXTRACTED,
        last_error="plan_extraction: invalid response",
    )
    enqueued = []
    monkeypatch.setattr(
        tasks,
        "run_site_pipeline_task",
        SimpleNamespace(
            using=lambda **kwargs: SimpleNamespace(
                enqueue=lambda site_id, **task_kwargs: enqueued.append(site_id)
            )
        ),
    )

    result = tasks.recover_site_pipeline_tasks()

    assert result == {"recovered": 0, "enqueued_sites": 1}
    assert enqueued == [clean_link.site_id]


def test_worker_startup_reopens_legacy_low_quality_plans(planned_link, monkeypatch):
    record = PlanRecord.objects.get(link=planned_link)
    record.confidence = 0.9
    record.save(update_fields=["confidence"])
    enqueued = []
    monkeypatch.setattr(
        tasks,
        "run_site_pipeline_task",
        SimpleNamespace(
            using=lambda **kwargs: SimpleNamespace(
                enqueue=lambda site_id, **task_kwargs: enqueued.append(site_id)
            )
        ),
    )

    result = tasks.recover_site_pipeline_tasks()

    planned_link.refresh_from_db()
    assert planned_link.pipeline_stage == Link.PipelineStage.EXTRACTED
    assert result == {"recovered": 0, "enqueued_sites": 1}
    assert enqueued == [planned_link.site_id]


def test_completed_discovery_is_not_repeated_by_pipeline(site, monkeypatch):
    site.last_discovered_at = timezone.now()
    site.save(update_fields=["last_discovered_at", "updated_at"])
    monkeypatch.setattr(
        services,
        "discover_and_store_links",
        lambda site: pytest.fail("discovery should not rerun"),
    )

    result = tasks.run_site_pipeline_task.call(site.pk)

    assert result == {"site_id": site.pk, "discovered": 0, "links": []}


def test_duplicate_pipeline_capture_does_not_park_link(site, monkeypatch):
    link = Link.objects.create(
        site=site,
        url="https://example.com/capturing",
        url_hash="capture-in-progress",
        review_state=Link.ReviewState.KEPT,
        pipeline_stage=Link.PipelineStage.DISCOVERED,
    )
    monkeypatch.setattr(
        services,
        "start_capture",
        lambda link: (_ for _ in ()).throw(RuntimeError("capture_in_progress")),
    )

    result = tasks.run_site_pipeline_task.call(site.pk, discover=False)

    link.refresh_from_db()
    assert result["links"] == []
    assert link.pipeline_stage == Link.PipelineStage.DISCOVERED
    assert link.last_error == ""


def test_task_on_already_published_link_is_completed(kept_link):
    kept_link.pipeline_stage = Link.PipelineStage.PUBLISHED
    kept_link.pipeline_task_state = "queued"
    kept_link.save(
        update_fields=["pipeline_stage", "pipeline_task_state", "updated_at"]
    )

    tasks.run_site_pipeline_task.call(
        kept_link.site_id, discover=False, link_id=kept_link.pk
    )

    kept_link.refresh_from_db()
    assert kept_link.pipeline_task_state == "completed"
    assert kept_link.last_error == ""


def test_no_acceptable_plans_is_handled_as_completed_quality_outcome(
    kept_link, monkeypatch
):
    kept_link.pipeline_stage = Link.PipelineStage.EXTRACTED
    kept_link.pipeline_task_state = "queued"
    kept_link.save(
        update_fields=["pipeline_stage", "pipeline_task_state", "updated_at"]
    )
    monkeypatch.setattr(services, "label_link_tables", lambda link, **kwargs: [])
    monkeypatch.setattr(
        services,
        "process_link_tables",
        lambda link: (_ for _ in ()).throw(
            services.llm.NoPlanRecordsError("no plan met the quality gate")
        ),
    )

    result = tasks.run_site_pipeline_task.call(
        kept_link.site_id, discover=False, link_id=kept_link.pk
    )

    kept_link.refresh_from_db()
    assert result["links"] == []
    assert kept_link.pipeline_task_state == "completed"
    assert kept_link.last_error.startswith("no_valid_plans:")


def test_no_accepted_table_completes_instead_of_failing(
    labeled_link, stub_llm, monkeypatch
):
    link = labeled_link
    link.pipeline_stage = Link.PipelineStage.EXTRACTED
    link.pipeline_task_state = "queued"
    link.save(update_fields=["pipeline_stage", "pipeline_task_state", "updated_at"])
    table = link.extracted_tables.get()
    table.rows.all().delete()
    table.rows.create(row_index=0, cells={"col-0": "About", "col-1": "us"})
    table.rows.create(row_index=1, cells={"col-0": "Contact", "col-1": "team"})

    result = tasks.run_site_pipeline_task.call(
        link.site_id, discover=False, link_id=link.pk
    )

    link.refresh_from_db()
    assert result["links"] == [link.pk]
    assert link.pipeline_task_state == "completed"
    assert link.pipeline_stage == Link.PipelineStage.NO_PRICE_TABLES
    assert link.last_error == ""


def test_llm_network_error_on_one_link_does_not_block_the_others(
    site, monkeypatch
):
    first = Link.objects.create(
        site=site,
        url="https://example.com/first",
        url_hash="first-link",
        review_state=Link.ReviewState.KEPT,
        pipeline_stage=Link.PipelineStage.EXTRACTED,
    )
    second = Link.objects.create(
        site=site,
        url="https://example.com/second",
        url_hash="second-link",
        review_state=Link.ReviewState.KEPT,
        pipeline_stage=Link.PipelineStage.EXTRACTED,
    )
    processed = []

    def fake_process(link):
        processed.append(link.pk)
        if link.pk == first.pk:
            raise services.llm.LlmError("network down")
        link.pipeline_stage = Link.PipelineStage.PLANS_EXTRACTED
        link.save()

    monkeypatch.setattr(services, "process_link_tables", fake_process)

    tasks.run_site_pipeline_task.call(site.pk, discover=False)

    assert set(processed) == {first.pk, second.pk}
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.last_error.startswith("classification:")
    assert second.last_error == ""


def test_discovery_failure_does_not_block_stored_links(site, monkeypatch):
    link = Link.objects.create(
        site=site,
        url="https://example.com/stored",
        url_hash="stored-link",
        review_state=Link.ReviewState.KEPT,
        pipeline_stage=Link.PipelineStage.EXTRACTED,
    )
    processed = []

    monkeypatch.setattr(
        services,
        "discover_and_store_links",
        lambda site: (_ for _ in ()).throw(services.llm.LlmError("network down")),
    )
    monkeypatch.setattr(
        services,
        "process_link_tables",
        lambda target: processed.append(target.pk),
    )

    tasks.run_site_pipeline_task.call(site.pk)

    assert processed == [link.pk]
