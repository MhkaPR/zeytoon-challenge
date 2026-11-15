"""Django Tasks (``django.tasks``) task bodies — no Celery anywhere (research R2).

Module-level functions wrapped with ``@task`` so the immediate backend runs them
synchronously in tests and a queued backend can run them in a worker in production.
Each body is per-link isolated (FR-051).

Task return values are stored as JSON by ``django.tasks`` backends, so every task
returns plain ids/dicts, never model instances.
"""

import logging
from datetime import timedelta

from django.db import models as django_models
from django.tasks import task

logger = logging.getLogger(__name__)


def _serializable(result):
    """Make a task return value JSON-safe (model instances become ``{"id": pk}``)."""
    if isinstance(result, django_models.Model):
        return {"id": result.pk}
    return result


def _get_link(link_id):
    from apps.pipeline.models import Link

    return Link.objects.filter(pk=link_id).first()


def _missing_link(link_id):
    logger.warning(
        "Skipping task for missing link %s",
        link_id,
        extra={"event": "pipeline_link_missing", "link_id": link_id},
    )
    return {"link_id": link_id, "skipped": "link_missing"}


@task
def run_capture_task(link_id, duration_ms=None):
    """Run a headless capture for a link (FR-016..FR-019)."""
    from apps.pipeline.services.v1.pipeline import start_capture

    link = _get_link(link_id)
    if link is None:
        return _missing_link(link_id)
    session = start_capture(link, duration_ms=duration_ms)
    return {"link_id": link_id, "session_id": session.pk, "state": session.state}


@task
def run_extraction_task(link_id):
    """Extract tables for a link (FR-020..FR-022)."""
    from apps.pipeline.services.v1.pipeline import extract_link_tables

    link = _get_link(link_id)
    if link is None:
        return _missing_link(link_id)
    tables = extract_link_tables(link)
    return {"link_id": link_id, "tables": len(tables)}


@task
def run_classification_task(link_id):
    """Classify each extracted table using the configured rules."""
    from apps.pipeline.services.v1.pipeline import classify_tables_for_link

    link = _get_link(link_id)
    if link is None:
        return _missing_link(link_id)
    link = classify_tables_for_link(link)
    return {"link_id": link_id, "stage": link.pipeline_stage}


@task
def run_labeling_task(link_id):
    """Label tables for a link (FR-032..FR-035)."""
    from apps.pipeline.services.v1.pipeline import label_link_tables

    link = _get_link(link_id)
    if link is None:
        return _missing_link(link_id)
    return _serializable(label_link_tables(link))


@task
def run_replay_task(link_id):
    """Run one replay cycle for a link (FR-039..FR-043)."""
    from apps.pipeline.replay import execute_replay_run

    link = _get_link(link_id)
    if link is None:
        return _missing_link(link_id)
    return _serializable(execute_replay_run(link))


# ---------------------------------------------------------------------------
# Site pipeline
# ---------------------------------------------------------------------------


def _set_task_state(link_pk, state):
    from django.utils import timezone

    from apps.pipeline.models import Link

    Link.objects.filter(pk=link_pk).update(
        pipeline_task_state=state, updated_at=timezone.now()
    )


def _claim_link(link_pk):
    """Atomically move a link to ``running``; False if another task owns it."""
    from django.utils import timezone

    from apps.pipeline.models import Link

    return bool(
        Link.objects.filter(pk=link_pk)
        .exclude(pipeline_task_state="running")
        .update(pipeline_task_state="running", updated_at=timezone.now())
    )


def _skip_stages():
    from apps.pipeline.models import Link

    return (
        Link.PipelineStage.PUBLISHED,
        Link.PipelineStage.NO_PRICE_TABLES,
        Link.PipelineStage.FLAGGED,
        Link.PipelineStage.DEAD_LETTERED,
        Link.PipelineStage.AWAITING_LLM_BUDGET,
    )


def _finalize_link_task(link_id):
    """Record the outcome of a per-link run; raise when it ended in failure."""
    from apps.pipeline.models import Link

    target = Link.objects.filter(pk=link_id).first()
    if target is None:
        return
    stage = Link.PipelineStage
    terminal = {
        stage.PLANS_EXTRACTED,
        stage.NO_PRICE_TABLES,
        stage.PUBLISHED,
        stage.FLAGGED,
        stage.DEAD_LETTERED,
        stage.AWAITING_LLM_BUDGET,
    }
    if not target.is_active or target.review_state != Link.ReviewState.KEPT:
        # Nothing will ever process this link; don't leave it ``queued`` forever.
        state = "idle"
    elif target.pipeline_stage == stage.AWAITING_LLM_BUDGET:
        state = "completed"
    elif target.last_error.startswith("no_valid_plans:"):
        state = "completed"
    elif target.last_error:
        state = "failed"
    elif target.pipeline_stage in terminal:
        state = "completed"
    elif target.pipeline_stage == stage.DISCOVERED:
        # A capture may already be running for this link. Leave it eligible for
        # worker recovery instead of recording a synthetic failure.
        state = "queued"
    else:
        state = "failed"
        target.last_error = f"pipeline_incomplete: stopped at {target.pipeline_stage}"
        target.save(update_fields=["last_error", "updated_at"])
    _set_task_state(link_id, state)
    if state == "failed":
        raise RuntimeError(target.last_error or "pipeline_incomplete")


@task
def run_site_pipeline_task(site_id, discover=True, link_id=None):
    """Discover once, then advance saved links from their persisted stage."""
    from apps.pipeline.models import Link, Site
    from apps.pipeline.services.v1 import pipeline as services

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
    if link_id is not None and not Link.objects.filter(pk=link_id, site=site).exists():
        # A link id from another site (or a deleted link) must not be touched.
        logger.warning(
            "Skipping pipeline task for link %s not in site %s",
            link_id,
            site_id,
            extra={"event": "pipeline_link_missing", "site_id": site_id},
        )
        return {
            "site_id": site.pk,
            "discovered": 0,
            "links": [],
            "skipped": "link_missing",
        }

    discovered = {"after_policy": 0}
    if discover and site.last_discovered_at is None:
        try:
            discovered = services.discover_and_store_links(site)
        except Exception:  # noqa: BLE001 - discovery must not block stored links
            logger.exception(
                "site_pipeline_discovery_failed",
                extra={"event": "site_pipeline_discovery_failed", "site_id": site.pk},
            )

    skip_stages = _skip_stages()
    candidates = Link.objects.filter(site=site, is_active=True).exclude(
        pipeline_stage__in=skip_stages
    )
    if link_id is not None:
        candidates = candidates.filter(pk=link_id)
    link_ids = list(candidates.order_by("pk").values_list("pk", flat=True))

    completed = []
    for pk in link_ids:
        link = Link.objects.filter(pk=pk).first()
        if link is None or not link.is_active:
            continue
        if link.pipeline_stage in skip_stages:
            continue
        if link.review_state != Link.ReviewState.KEPT:
            continue
        if link.last_error and link.pipeline_task_state != "queued":
            continue
        # Atomic claim: replaces check-then-act so two tasks can't process one link.
        if not _claim_link(pk):
            continue
        link.refresh_from_db()
        if link.pipeline_stage in skip_stages:
            _set_task_state(pk, "completed")
            continue

        stage = "capture"
        try:
            if link.pipeline_stage == Link.PipelineStage.DISCOVERED:
                stage = "capture"
                try:
                    services.start_capture(link)
                except services.CaptureInProgress:
                    # A duplicate site task may have lost the race to create the
                    # unique non-terminal capture session. The winning task owns
                    # this stage; don't park the link as failed.
                    _set_task_state(pk, "queued")
                    continue
                except RuntimeError as exc:
                    if str(exc) != "capture_in_progress":
                        raise
                    _set_task_state(pk, "queued")
                    continue
                link.refresh_from_db()
            if link.pipeline_stage == Link.PipelineStage.CAPTURED:
                stage = "extraction"
                services.extract_link_tables(link)
                link.refresh_from_db()
            if link.pipeline_stage == Link.PipelineStage.EXTRACTED:
                stage = "classification"
                services.process_link_tables(link)
                link.refresh_from_db()
                if not link.plan_records.exists():
                    completed.append(pk)
                    _set_task_state(pk, "completed")
                    continue
            completed.append(pk)
            link.last_error = ""
            link.save(update_fields=["last_error", "updated_at"])
            waiting_for_capture = (
                link.pipeline_stage == Link.PipelineStage.DISCOVERED
                and link.capture_sessions.filter(
                    state__in=link.capture_sessions.model.NON_TERMINAL
                ).exists()
            )
            _set_task_state(pk, "queued" if waiting_for_capture else "completed")
        except services.llm.LlmBudgetExhausted as exc:
            # Park the link until the admin raises the budget; rerun_link_stages
            # reads the stage after the last ``:`` to decide where to resume.
            budget_stage = getattr(exc, "stage", None)
            if budget_stage not in ("labeling", "classification", "schema_extraction"):
                budget_stage = "classification"
            from django.utils import timezone

            Link.objects.filter(pk=pk).update(
                pipeline_stage=Link.PipelineStage.AWAITING_LLM_BUDGET,
                last_error=f"awaiting_llm_budget:{budget_stage}",
                pipeline_task_state="completed",
                updated_at=timezone.now(),
            )
            logger.info(
                "site_pipeline_awaiting_budget",
                extra={"event": "site_pipeline_awaiting_budget", "link_id": pk},
            )
        except Exception as exc:  # noqa: BLE001 - per-link isolation (FR-051)
            link.refresh_from_db()
            if isinstance(exc, services.llm.NoPlanRecordsError):
                link.last_error = f"no_valid_plans: {exc}"[:512]
                link.save(update_fields=["last_error", "updated_at"])
                _set_task_state(pk, "completed")
                logger.info(
                    "site_pipeline_no_valid_plans",
                    extra={"event": "site_pipeline_no_valid_plans", "link_id": pk},
                )
                continue
            # ``stage`` was tracked by this loop, so a dead-lettered link (whose
            # persisted stage is no longer the stage that failed) still reports
            # the real failing stage.
            link.last_error = f"{stage}: {str(exc)[:450]}"
            link.save(update_fields=["last_error", "updated_at"])
            _set_task_state(pk, "failed")
            logger.exception(
                "site_pipeline_link_failed",
                extra={"event": "site_pipeline_link_failed", "link_id": pk},
            )

    if link_id is not None:
        _finalize_link_task(link_id)

    return {
        "site_id": site.pk,
        "discovered": discovered["after_policy"],
        "links": completed,
    }


# ---------------------------------------------------------------------------
# Recovery
# ---------------------------------------------------------------------------


def _task_site_and_link(result):
    """Read ``(site_id, link_id)`` from a stored task whether args or kwargs were used."""
    payload = result.args_kwargs or {}
    args = payload.get("args") or []
    kwargs = payload.get("kwargs") or {}
    site_pk = args[0] if args else kwargs.get("site_id")
    link_pk = kwargs.get("link_id")
    if link_pk is None and len(args) > 2:
        link_pk = args[2]
    return site_pk, link_pk


def _active_task_scope(base, status_enum):
    """Return ``(site_wide_site_ids, link_ids)`` covered by READY/RUNNING tasks."""
    site_wide, link_ids = set(), set()
    active = base.filter(status__in=(status_enum.READY, status_enum.RUNNING))
    for result in active.only("pk", "args_kwargs"):
        site_pk, link_pk = _task_site_and_link(result)
        if link_pk:
            link_ids.add(link_pk)
        elif site_pk is not None:
            site_wide.add(site_pk)
    return site_wide, link_ids


def recover_site_pipeline_tasks(backend_name="default", stale_after_seconds=None):
    """Reconcile pipeline state after a crash and requeue unfinished work.

    Recovery is state-based, not only task-row-based:

    1. ``RUNNING`` site-pipeline tasks (optionally only those older than
       ``stale_after_seconds``) are reset to ``READY``.
    2. Every link still marked ``queued``/``running`` and every non-terminal capture
       session that is *not covered* by a READY/RUNNING task is orphaned (its task
       failed, was deleted, or was never enqueued). Orphaned sessions are failed and
       orphaned links go back to ``idle``.
    3. Stale/incomplete markers are repaired.
    4. A site-wide task is enqueued for every site that still has unfinished links
       and no site-wide task.

    Leave ``stale_after_seconds`` as ``None`` for single-worker startup recovery
    (nothing else is alive, so no grace period). With several workers, set it: it also
    becomes the grace period before an orphan is touched, so live work isn't reset.
    """
    from django.db.models import Q
    from django.utils import timezone
    from django_tasks_db.compat import TaskResultStatus
    from django_tasks_db.models import DBTaskResult

    from apps.pipeline.models import CaptureSession, Link, Site
    from apps.pipeline.services.v1 import pipeline as services

    now = timezone.now()
    grace_cutoff = now - timedelta(seconds=stale_after_seconds) if stale_after_seconds else None
    task_path = getattr(
        run_site_pipeline_task,
        "module_path",
        "apps.pipeline.tasks.run_site_pipeline_task",
    )
    base = DBTaskResult.objects.filter(
        task_path=task_path, backend_name=backend_name
    )

    # 1. Interrupted RUNNING tasks -> READY.
    running = base.filter(status=TaskResultStatus.RUNNING)
    if grace_cutoff is not None:
        running = running.filter(started_at__lt=grace_cutoff)
    interrupted_pks = []
    interrupted_link_ids = set()
    interrupted_site_ids = set()
    for result in running.only("pk", "args_kwargs"):
        site_pk, link_pk = _task_site_and_link(result)
        interrupted_pks.append(result.pk)
        if link_pk:
            interrupted_link_ids.add(link_pk)
        elif site_pk is not None:
            interrupted_site_ids.add(site_pk)

    interrupted_count = 0
    if interrupted_pks:
        # Close the dead workers' sessions *before* their tasks become READY (and so
        # "covered"), otherwise the resumed task would hit capture_in_progress forever.
        CaptureSession.objects.filter(
            Q(link_id__in=interrupted_link_ids)
            | Q(link__site_id__in=interrupted_site_ids),
            state__in=CaptureSession.NON_TERMINAL,
        ).update(
            state=CaptureSession.State.FAILED,
            error="worker_interrupted",
            updated_at=now,
        )
        interrupted_count = DBTaskResult.objects.filter(pk__in=interrupted_pks).update(
            status=TaskResultStatus.READY,
            started_at=None,
            finished_at=None,
            worker_ids=[],
            exception_class_path="",
            traceback="",
            run_after=now,
        )
    if interrupted_link_ids:
        Link.objects.filter(pk__in=interrupted_link_ids).update(
            pipeline_task_state="queued", updated_at=now
        )
    if interrupted_site_ids:
        # A site-wide task was interrupted mid-link: reset its links so the requeued
        # task resumes them instead of skipping them as running.
        Link.objects.filter(
            site_id__in=interrupted_site_ids, pipeline_task_state="running"
        ).update(pipeline_task_state="idle", updated_at=now)

    # 2. Orphans: work that no READY/RUNNING task covers.
    site_wide_site_ids, covered_link_ids = _active_task_scope(base, TaskResultStatus)
    uncovered_link = ~(
        Q(site_id__in=site_wide_site_ids) | Q(pk__in=covered_link_ids)
    )
    orphan_links = Link.objects.filter(
        uncovered_link, pipeline_task_state__in=("queued", "running")
    )
    if grace_cutoff is not None:
        orphan_links = orphan_links.filter(updated_at__lt=grace_cutoff)
    orphan_link_ids = list(orphan_links.values_list("pk", flat=True))

    orphan_sessions = CaptureSession.objects.filter(
        ~(
            Q(link__site_id__in=site_wide_site_ids)
            | Q(link_id__in=covered_link_ids)
        ),
        state__in=CaptureSession.NON_TERMINAL,
    )
    if grace_cutoff is not None:
        orphan_sessions = orphan_sessions.filter(updated_at__lt=grace_cutoff)
    orphan_sessions.update(
        state=CaptureSession.State.FAILED,
        error="worker_interrupted",
        updated_at=now,
    )
    if orphan_link_ids:
        Link.objects.filter(pk__in=orphan_link_ids).update(
            pipeline_task_state="idle", updated_at=now
        )

    # 3. Repair stale / incomplete markers.
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
            updated_at=now,
        )

    # Older worker runs could leave a synthetic incomplete marker on links whose
    # persisted stage is still resumable. Real stage errors stay parked for an
    # operator retry.
    unfinished_stages = (
        Link.PipelineStage.DISCOVERED,
        Link.PipelineStage.CAPTURED,
        Link.PipelineStage.EXTRACTED,
    )
    Link.objects.filter(
        is_active=True,
        pipeline_stage__in=unfinished_stages,
        last_error__startswith="pipeline_incomplete:",
    ).update(last_error="", updated_at=now)

    # 4. Enqueue a site-wide task for every site with unfinished links. A queued
    # per-link rerun only covers one link, so it doesn't suppress this.
    unfinished_site_ids = set(
        Link.objects.filter(
            is_active=True,
            review_state=Link.ReviewState.KEPT,
            pipeline_stage__in=unfinished_stages,
            last_error="",
        )
        .exclude(pipeline_task_state="running")
        .values_list("site_id", flat=True)
    )
    site_ids = unfinished_site_ids - site_wide_site_ids
    for site_id in Site.objects.filter(pk__in=site_ids).values_list("pk", flat=True):
        run_site_pipeline_task.using(backend=backend_name).enqueue(
            site_id, discover=False
        )
    summary = {
        "recovered": interrupted_count,
        "orphaned_links": len(orphan_link_ids),
        "enqueued_sites": len(site_ids),
    }
    logger.info(
        "pipeline_recovery %s",
        summary,
        extra={"event": "pipeline_recovery", **summary},
    )
    return summary
