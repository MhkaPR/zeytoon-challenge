from types import SimpleNamespace

import pytest
from django.db import transaction
from django.tasks.base import TASK_MAX_PRIORITY

from apps.admin_console import tasks
from apps.pipeline.models import Link

pytestmark = pytest.mark.django_db


def test_link_rerun_is_accepted_once_while_already_queued(
    operator_client, kept_link, monkeypatch
):
    enqueued = []
    monkeypatch.setattr(
        tasks,
        "run_site_pipeline_task",
        SimpleNamespace(
            using=lambda **options: SimpleNamespace(
                enqueue=lambda *args, **kwargs: enqueued.append((args, kwargs, options))
            )
        ),
    )
    monkeypatch.setattr(transaction, "on_commit", lambda callback: callback())
    kept_link.last_error = "plan_extraction: invalid response"
    kept_link.pipeline_stage = "classified"
    kept_link.save(update_fields=["last_error", "pipeline_stage", "updated_at"])
    endpoint = f"/api/v1/ops/links/{kept_link.pk}/rerun"

    first = operator_client.post(endpoint)
    second = operator_client.post(endpoint)

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["queued"] is True
    assert second.json()["link"]["pipeline_task_state"] == "queued"
    assert len(enqueued) == 1
    assert enqueued[0][2] == {"priority": TASK_MAX_PRIORITY}


def test_distinct_link_retries_are_enqueued_independently(
    operator_client, kept_link, monkeypatch
):
    enqueued = []
    monkeypatch.setattr(
        tasks,
        "run_site_pipeline_task",
        SimpleNamespace(
            using=lambda **options: SimpleNamespace(
                enqueue=lambda *args, **kwargs: enqueued.append((args, kwargs, options))
            )
        ),
    )
    monkeypatch.setattr(transaction, "on_commit", lambda callback: callback())
    second_link = Link.objects.create(
        site=kept_link.site,
        url="https://example.com/servers",
        url_hash="second-kept-hash",
        review_state=Link.ReviewState.KEPT,
        pipeline_stage=Link.PipelineStage.EXTRACTED,
        last_error="plan_extraction: previous extraction failed",
    )

    for link in (kept_link, second_link):
        response = operator_client.post(f"/api/v1/ops/links/{link.pk}/rerun")
        assert response.status_code == 202
        assert response.json()["link"]["pipeline_task_state"] == "queued"

    assert len(enqueued) == 2
    assert {kwargs["link_id"] for _, kwargs, _ in enqueued} == {
        kept_link.pk,
        second_link.pk,
    }
    assert all(options == {"priority": TASK_MAX_PRIORITY} for _, _, options in enqueued)
