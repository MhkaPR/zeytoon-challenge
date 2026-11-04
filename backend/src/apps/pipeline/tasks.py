"""Django Tasks (``django.tasks``) task bodies — no Celery anywhere (research R2).

Module-level functions wrapped with ``@task`` so the immediate backend runs them
synchronously in tests and a queued backend can run them in a worker in production.
Each body is per-link isolated (FR-051).
"""

from django.tasks import task


@task
def run_capture_task(link_id, duration_ms=None):
    """Run a headless capture for a link (FR-016..FR-019)."""
    from apps.pipeline.services.v1 import pipeline as services
    from apps.pipeline.models import Link
    from apps.pipeline.services import start_capture

    return start_capture(Link.objects.get(pk=link_id), duration_ms=duration_ms)


@task
def run_extraction_task(link_id):
    """Extract tables for a link (FR-020..FR-022)."""
    from apps.pipeline.models import Link
    from apps.pipeline.services import extract_link_tables

    return extract_link_tables(Link.objects.get(pk=link_id))


@task
def run_classification_task(link_id):
    """Classify each extracted table using the configured rules."""
    from apps.pipeline.models import Link
    from apps.pipeline.services import classify_tables_for_link

    return classify_tables_for_link(Link.objects.get(pk=link_id))


@task
def run_labeling_task(link_id):
    """Label tables for a link (FR-032..FR-035)."""
    from apps.pipeline.models import Link
    from apps.pipeline.services import label_link_tables

    return label_link_tables(Link.objects.get(pk=link_id))


@task
def run_replay_task(link_id):
    """Run one replay cycle for a link (FR-039..FR-043)."""
    from apps.pipeline.models import Link
    from apps.pipeline.replay import execute_replay_run

    return execute_replay_run(Link.objects.get(pk=link_id))


@task
def run_site_pipeline_task(site_id, discover=True, link_id=None):
    """Discover once, then advance saved links from their persisted stage."""
    import logging

    from apps.pipeline.services.v1 import pipeline as services
    from apps.pipeline.models import Link, Site

    logger = logging.getLogger(__name__)
    site = Site.objects.filter(pk=site_id).first()
    if site is None:
        # A persisted task can outlive its site (for example after test data or an
        # operator cleanup). Treat it as stale work instead of retrying forever.
        logger.warning(
            "Skipping pipeline task for missing site %s",
            site_id,
            extra={"event": "pipeline_site_missing", "site_id": site_id},
        )
        return {
            "site_id": site_id,
            "discovered": 0,
            "links": [],
            "skipped": "site_missing",
        }
    discovered = {"after_policy": 0}
    if discover and site.last_discovered_at is None:
        discovered = services.discover_and_store_links(site)
    completed = []

    links = Link.objects.filter(site=site, is_active=True).exclude(
        pipeline_stage__in=(
            Link.PipelineStage.PUBLISHED,
            Link.PipelineStage.NO_PRICE_TABLES,
            Link.PipelineStage.FLAGGED,
            Link.PipelineStage.DEAD_LETTERED,
            Link.PipelineStage.AWAITING_LLM_BUDGET,
        )
    )
    if link_id is not None:
        links = links.filter(pk=link_id)

    if link_id is not None:
        Link.objects.filter(pk=link_id).update(pipeline_task_state="running")

    for link in links:
        link.refresh_from_db()
        if link.pipeline_stage == Link.PipelineStage.AWAITING_LLM_BUDGET:
            continue
        if link.review_state != Link.ReviewState.KEPT:
            continue
        if link.last_error and link.pipeline_task_state != "queued":
            continue
        Link.objects.filter(pk=link.pk).update(pipeline_task_state="running")
        try:
            if link.pipeline_stage == Link.PipelineStage.DISCOVERED:
                try:
                    services.start_capture(link)
                except RuntimeError as exc:
                    if str(exc) == "capture_in_progress":
                        # A duplicate site task may have lost the race to create
                        # the unique non-terminal capture session. The winning
                        # task owns this stage; don't park the link as failed.
                        Link.objects.filter(pk=link.pk).update(
                            pipeline_task_state="queued"
                        )
                        continue
                    raise
                link.refresh_from_db()
            if link.pipeline_stage == Link.PipelineStage.CAPTURED:
                services.extract_link_tables(link)
                link.refresh_from_db()
            if link.pipeline_stage == Link.PipelineStage.EXTRACTED:
                services.process_link_tables(link)
                link.refresh_from_db()
                if not link.plan_records.exists():
                    completed.append(link.pk)
                    Link.objects.filter(pk=link.pk).update(
                        pipeline_task_state="completed"
                    )
                    continue
            completed.append(link.pk)
            link.last_error = ""
            link.save(update_fields=["last_error", "updated_at"])
            waiting_for_capture = (
                link.pipeline_stage == Link.PipelineStage.DISCOVERED
                and link.capture_sessions.filter(
                    state__in=link.capture_sessions.model.NON_TERMINAL
                ).exists()
            )
            Link.objects.filter(pk=link.pk).update(
                pipeline_task_state="queued" if waiting_for_capture else "completed"
            )
        except Exception as exc:
            link.refresh_from_db()
            if isinstance(exc, services.llm.NoPlanRecordsError):
                link.last_error = f"no_valid_plans: {exc}"[:512]
                link.save(update_fields=["last_error", "updated_at"])
                Link.objects.filter(pk=link.pk).update(pipeline_task_state="completed")
                logger.info(
                    "site_pipeline_no_valid_plans",
                    extra={"event": "site_pipeline_no_valid_plans", "link_id": link.pk},
                )
                continue
            failed_stage = {
                Link.PipelineStage.DISCOVERED: "capture",
                Link.PipelineStage.CAPTURED: "extraction",
                Link.PipelineStage.EXTRACTED: "classification",
            }.get(link.pipeline_stage, link.pipeline_stage)
            link.last_error = f"{failed_stage}: {str(exc)[:450]}"
            link.save(update_fields=["last_error", "updated_at"])
            Link.objects.filter(pk=link.pk).update(pipeline_task_state="failed")
            logger.exception(
                "site_pipeline_link_failed",
                extra={"event": "site_pipeline_link_failed", "link_id": link.pk},
            )

    if link_id is not None:
        target = Link.objects.filter(pk=link_id).first()
        if target is not None:
            terminal_stages = {
                Link.PipelineStage.PLANS_EXTRACTED,
                Link.PipelineStage.NO_PRICE_TABLES,
                Link.PipelineStage.PUBLISHED,
                Link.PipelineStage.FLAGGED,
                Link.PipelineStage.DEAD_LETTERED,
                Link.PipelineStage.AWAITING_LLM_BUDGET,
            }
            if target.last_error.startswith("no_valid_plans:"):
                state = "completed"
            elif target.last_error:
                state = "failed"
            elif target.pipeline_stage in terminal_stages:
                state = "completed"
            elif (
                target.pipeline_stage == Link.PipelineStage.DISCOVERED
                and not target.last_error
            ):
                # A capture may already be running for this link. Leave it eligible
                # for worker recovery instead of recording a synthetic failure.
                state = "queued"
            else:
                state = "failed"
                target.last_error = (
                    f"pipeline_incomplete: stopped at {target.pipeline_stage}"
                )
                target.save(update_fields=["last_error", "updated_at"])
            Link.objects.filter(pk=link_id).update(pipeline_task_state=state)
            if state == "failed":
                raise RuntimeError(target.last_error or "pipeline_incomplete")

    return {
        "site_id": site.pk,
        "discovered": discovered["after_policy"],
        "links": completed,
    }


def recover_site_pipeline_tasks(backend_name="default"):
    """Requeue interrupted pipeline work and unqueued, clean in-progress links."""
    from django.utils import timezone
    from django_tasks_db.compat import TaskResultStatus
    from django_tasks_db.models import DBTaskResult

    from apps.pipeline.services.v1 import pipeline as services
    from apps.pipeline.models import CaptureSession, Link

    task_path = "pipeline.tasks.run_site_pipeline_task"
    interrupted = DBTaskResult.objects.filter(
        task_path=task_path,
        backend_name=backend_name,
        status=TaskResultStatus.RUNNING,
    )
    interrupted_link_ids = [
        result.args_kwargs.get("kwargs", {}).get("link_id")
        for result in interrupted.only("args_kwargs")
    ]
    interrupted_count = interrupted.update(
        status=TaskResultStatus.READY,
        started_at=None,
        finished_at=None,
        worker_ids=[],
        exception_class_path="",
        traceback="",
        run_after=timezone.now(),
    )
    Link.objects.filter(pk__in=[pk for pk in interrupted_link_ids if pk]).update(
        pipeline_task_state="queued"
    )

    active_tasks = DBTaskResult.objects.filter(
        task_path=task_path,
        backend_name=backend_name,
        status__in=(TaskResultStatus.READY, TaskResultStatus.RUNNING),
    )
    queued_site_ids = {
        result.args_kwargs["args"][0]
        for result in active_tasks.only("args_kwargs")
        if result.args_kwargs.get("args")
    }
    # A killed worker can leave a capture session in ``recording`` forever.
    # Such a session blocks start_capture, which makes the resumed site task
    # return successfully without advancing the queued link. Only close sessions
    # when no pipeline task for that site is currently queued or running.
    CaptureSession.objects.filter(
        link__is_active=True,
        link__pipeline_stage=Link.PipelineStage.DISCOVERED,
        link__site_id__in=Link.objects.filter(
            is_active=True,
            review_state=Link.ReviewState.KEPT,
            pipeline_stage=Link.PipelineStage.DISCOVERED,
        )
        .exclude(site_id__in=queued_site_ids)
        .values("site_id"),
        state__in=CaptureSession.NON_TERMINAL,
    ).update(state=CaptureSession.State.FAILED, error="worker_interrupted")
    stale_plan_links = []
    for link in Link.objects.filter(
        is_active=True,
        review_state=Link.ReviewState.KEPT,
        pipeline_stage=Link.PipelineStage.PLANS_EXTRACTED,
        last_error="",
    ).prefetch_related("plan_records"):
        records = list(link.plan_records.all())
        if not records or any(
            not services._plan_is_complete(
                record.values, record.plan_type, record.confidence
            )
            for record in records
        ):
            stale_plan_links.append(link.pk)
    if stale_plan_links:
        Link.objects.filter(pk__in=stale_plan_links).update(
            pipeline_stage=Link.PipelineStage.EXTRACTED,
            last_error="",
        )
    # Older worker runs could leave a synthetic incomplete marker on links whose
    # persisted stage is still resumable. Clear that marker so startup recovery
    # can enqueue them; real stage errors remain parked for an operator retry.
    Link.objects.filter(
        is_active=True,
        pipeline_stage__in=(
            Link.PipelineStage.DISCOVERED,
            Link.PipelineStage.CAPTURED,
            Link.PipelineStage.EXTRACTED,
        ),
        last_error__startswith="pipeline_incomplete:",
    ).update(last_error="")
    unfinished_site_ids = set(
        Link.objects.filter(
            is_active=True,
            review_state=Link.ReviewState.KEPT,
            pipeline_stage__in=(
                Link.PipelineStage.DISCOVERED,
                Link.PipelineStage.CAPTURED,
                Link.PipelineStage.EXTRACTED,
            ),
            last_error="",
        ).values_list("site_id", flat=True)
    )
    site_ids = unfinished_site_ids - queued_site_ids
    if site_ids:
        from apps.pipeline.models import Site

        for site_id in Site.objects.filter(pk__in=site_ids).values_list(
            "pk", flat=True
        ):
            run_site_pipeline_task.using(backend=backend_name).enqueue(
                site_id, discover=False
            )
    return {"recovered": interrupted_count, "enqueued_sites": len(site_ids)}
