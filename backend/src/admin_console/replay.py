"""Scheduled replay orchestration (FR-037..FR-039, research R14).

One replay cycle per link: materialize the stored *before* trace, hand it to domtrack's
``compare_replay`` (replay + record-during-replay + diff in a single library call), store
the *after* recording via the artifact store, record a :class:`ReplayRun` with domtrack's
own stats/failures/diff summary, re-extract + re-map + re-publish from the fresh recording
(so a removed item is retired rather than left stale, FR-036/FR-039), and recompute the
link's failure rate from domtrack's reported failures over the trailing window (FR-040).

Nothing here re-derives a domtrack capability — replay, record, diff, and failure
reporting all come from the library (SC-017).
"""

import tempfile

from django.utils import timezone

from accounts.exceptions import ApiError
from admin_console import artifacts, constants, domtrack_client, events
from admin_console.models import Link, ReplayRun, Trace


def _before_trace_path(link):
    trace = link.current_trace
    if trace is None:
        raise ApiError(
            "trace_required",
            "A stored trace is required before replay.",
            http_status=409,
        )
    return trace, artifacts.materialize(trace.storage_key, backend=trace.storage_backend)


def _summarize(compare_result):
    """Flatten domtrack's compare result into JSON-safe fields (library shapes only)."""
    stats = compare_result.stats
    failures = [
        {
            "selector": getattr(failure, "selector", None),
            "reason": getattr(failure, "reason", None),
        }
        for failure in (getattr(stats, "failures", []) or [])
    ]
    return {
        "diff_summary": dict(compare_result.diff.summary or {}),
        "stats_applied": int(getattr(stats, "applied", 0) or 0),
        "stats_skipped": int(getattr(stats, "skipped", 0) or 0),
        "stats_failed": int(getattr(stats, "failed", 0) or 0),
        "failures": failures,
    }


def _store_after_trace(link, after_path, capture_session=None):
    with open(after_path, "rb") as handle:
        after_bytes = handle.read()
    key, backend, size, digest = artifacts.save_trace(after_bytes)
    return Trace.objects.create(
        link=link,
        capture_session=capture_session,
        captured_at=timezone.now(),
        origin=Trace.Origin.REPLAY_RECORDING,
        storage_key=key,
        storage_backend=backend,
        byte_size=size,
        content_sha256=digest,
        is_valid_trace=True,
    )


def _recompute_failure_rate(link):
    """Derive the link failure rate from domtrack's reported failures (FR-040, R14)."""
    window = max(1, constants.failure_rate_window_runs())
    runs = list(ReplayRun.objects.filter(link=link).order_by("-created_at")[:window])
    if not runs:
        rate = 0.0
    else:
        applied = sum(run.stats_applied for run in runs)
        failed = sum(run.stats_failed for run in runs)
        total = applied + failed
        rate = (failed / total) if total else 0.0
    link.failure_rate = rate
    link.save(update_fields=["failure_rate", "updated_at"])
    return rate


def execute_replay_run(link, scheduled_for=None):
    """Run one replay cycle for ``link`` and apply its diff (FR-037..FR-039)."""
    from admin_console.services import (
        evaluate_failure_alert,
        extract_tables_for_link,
        get_current_recipe,
        publish_link_data,
    )

    recipe = get_current_recipe(link)
    before_trace, before_path = _before_trace_path(link)
    run = ReplayRun.objects.create(
        link=link,
        recipe=recipe,
        scheduled_for=scheduled_for or timezone.now(),
        started_at=timezone.now(),
        state=ReplayRun.State.RUNNING,
        before_trace=before_trace,
    )

    try:
        output_dir = tempfile.mkdtemp(prefix="ops-replay-")
        compare_result = domtrack_client.compare_replay(
            before_path,
            constants.replay_config(),
            {"output_dir": output_dir},
        )
        after_trace = _store_after_trace(link, compare_result.after_path)

        # Adopt the fresh recording, re-extract from it, and re-publish the recipe's data.
        link.current_trace = after_trace
        link.save(update_fields=["current_trace", "updated_at"])
        extract_tables_for_link(link)
        publish_link_data(link)

        summary = _summarize(compare_result)
        run.after_trace = after_trace
        run.diff_summary = summary["diff_summary"]
        run.stats_applied = summary["stats_applied"]
        run.stats_skipped = summary["stats_skipped"]
        run.stats_failed = summary["stats_failed"]
        run.failures = summary["failures"]
        run.diff_applied = True
        run.state = ReplayRun.State.SUCCEEDED
        run.finished_at = timezone.now()
        run.save()
    except Exception as exc:  # noqa: BLE001 - record failure, never crash the batch
        run.state = ReplayRun.State.FAILED
        run.finished_at = timezone.now()
        run.diff_summary = {"error": str(exc)[:500]}
        run.save()
        raise
    finally:
        link.last_replay_at = timezone.now()
        link.save(update_fields=["last_replay_at", "updated_at"])

    rate = _recompute_failure_rate(link)
    stale_seconds = 0.0
    if link.current_trace and link.current_trace.captured_at:
        stale_seconds = (timezone.now() - link.current_trace.captured_at).total_seconds()
    events.replay_run_completed(link, rate, stale_seconds, run.state)
    evaluate_failure_alert(link)
    link.refresh_from_db()
    return {
        "replay_run_id": run.pk,
        "state": run.state,
        "failure_rate": rate,
        "diff_applied": run.diff_applied,
        "diff_summary": run.diff_summary,
    }
