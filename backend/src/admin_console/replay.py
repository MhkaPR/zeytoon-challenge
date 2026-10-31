"""Scheduled replay and change detection (FR-039..FR-043).

One ``domtrack compare`` call replays the previous trace, records the replayed page, and
diffs the two (FR-040). Every detected change is classified **content** or
**structural**; a change touching a plans table triggers LLM re-extraction, and a
structural change re-runs table discovery + classification first (FR-042). A change that
does not touch a plans table runs no LLM work (FR-043).
"""

import os

from django.db import transaction
from django.utils import timezone

from admin_console import artifacts, constants, domtrack_client, events, services
from admin_console.models import (
    ChangeRecord,
    Link,
    ReplayRun,
    TableClassification,
    Trace,
)


def execute_replay_run(link, actor=None):
    from admin_console import llm

    before_trace = link.current_trace
    run = ReplayRun.objects.create(
        link=link,
        state=ReplayRun.State.RUNNING,
        started_at=timezone.now(),
        before_trace=before_trace,
    )
    if before_trace is None:
        _fail(run, link, ["no_before_trace"])
        return run

    before_path = services._materialize(before_trace)
    try:
        result = domtrack_client.compare_replay(
            before_path,
            replay_config=constants.replay_config(),
            recording={"output_dir": os.path.dirname(before_path)},
        )
    except llm.LlmBudgetExhausted:
        run.state = ReplayRun.State.AWAITING_LLM_BUDGET
        run.save(update_fields=["state", "updated_at"])
        return run
    except Exception as exc:  # noqa: BLE001 - recorded as a replay failure
        _fail(run, link, [str(exc)[:200]])
        return run
    finally:
        _cleanup(before_path)

    try:
        after_trace = _store_after_trace(link, result.after_path)
    except Exception as exc:  # noqa: BLE001
        _fail(run, link, [f"after_trace:{exc}"[:200]])
        return run

    run.after_trace = after_trace
    changes = _classify_changes(link, result.diff)
    plans_touched = any(change["touches_plans_table"] for change in changes)
    structural = any(
        change["change_kind"] == ChangeRecord.Kind.STRUCTURAL for change in changes
    )

    reextracted = False
    if plans_touched:
        try:
            if structural:
                services.extract_link_tables(link)
                services.classify_link_tables(link)
            services.extract_link_plans(link)
            services.publish_link_plans(link)
            services.retire_missing_plans(link, services.unignored_plan_keys(link))
            reextracted = True
        except llm.LlmBudgetExhausted:
            run.state = ReplayRun.State.AWAITING_LLM_BUDGET
            run.save(update_fields=["state", "updated_at"])
            return run
        except Exception as exc:  # noqa: BLE001
            _fail(run, link, [f"reextract:{exc}"[:200]])
            return run

    with transaction.atomic():
        ChangeRecord.objects.filter(replay_run=run).delete()
        for change in changes:
            ChangeRecord.objects.create(
                replay_run=run,
                change_kind=change["change_kind"],
                touches_plans_table=change["touches_plans_table"],
                classification=_resolve_classification(link, change),
                summary=change["summary"],
            )

    summary = dict(getattr(result, "summary", {}) or {})
    run.diff_summary = summary
    run.reextracted = reextracted
    run.stats_applied = int(summary.get("added", 0)) + int(summary.get("changed", 0))
    run.stats_skipped = 0 if reextracted else int(summary.get("changed", 0))
    run.stats_failed = 0
    run.failures = []
    run.state = ReplayRun.State.SUCCEEDED
    run.finished_at = timezone.now()
    run.save()
    link.last_replay_at = run.finished_at
    link.save(update_fields=["last_replay_at", "updated_at"])
    services.recompute_failure_rate(link)
    events.replay_completed(run, len(changes), reextracted)
    return run


def _cleanup(path):
    try:
        os.unlink(path)
    except OSError:
        pass


def _store_after_trace(link, after_path):
    with open(after_path, "rb") as handle:
        data = handle.read()
    key, backend, size, digest = artifacts.save_trace(data)
    return Trace.objects.create(
        link=link,
        captured_at=timezone.now(),
        origin=Trace.Origin.REPLAY_RECORDING,
        storage_key=key,
        storage_backend=backend,
        byte_size=size,
        content_sha256=digest,
        is_valid_trace=True,
    )


def _classify_changes(link, diff):
    """Turn a domtrack diff into content/structural change descriptors (FR-041)."""
    changes = []
    for path, _entry in getattr(diff, "added", []) or []:
        changes.append(_change(link, path, ChangeRecord.Kind.STRUCTURAL))
    for path, _entry in getattr(diff, "removed", []) or []:
        changes.append(_change(link, path, ChangeRecord.Kind.STRUCTURAL))
    for change in getattr(diff, "changed", []) or []:
        if getattr(change, "text_changed", False):
            changes.append(
                _change(link, getattr(change, "path", ""), ChangeRecord.Kind.CONTENT)
            )
    return changes


def _change(link, path, kind):
    classification = _classification_for_path(link, path)
    return {
        "change_kind": kind,
        "touches_plans_table": classification is not None,
        "classification": classification,
        "summary": {"path": path},
    }


def _resolve_classification(link, change):
    """Keep only a live classification reference after a structural re-extraction.

    Classifications captured before re-extraction can be deleted together with their
    tables, so re-resolve from the (possibly new) tables before writing the record.
    """
    classification = change["classification"]
    if classification is None:
        return None
    if TableClassification.objects.filter(pk=classification.pk).exists():
        return classification
    return _classification_for_path(link, change["summary"].get("path", ""))


def _classification_for_path(link, path):
    """Match a diff path to a plans-table classification, if any (best effort)."""
    if not path:
        return None
    normalized = str(path).lower()
    for table in link.extracted_tables.all():
        classification = getattr(table, "classification", None)
        if classification is None or not classification.is_plans_table:
            continue
        tokens = {table.parent.lower()} if table.parent else set()
        for column in table.columns.all():
            tokens.update(token for token in str(column.path).lower().replace(">", " ").split())
        tokens = {token for token in tokens if token}
        if any(token and token in normalized for token in tokens):
            return classification
    return None


def _fail(run, link, failures):
    run.state = ReplayRun.State.FAILED
    run.failures = failures
    run.diff_summary = {"error": failures[0] if failures else "unknown"}
    run.finished_at = timezone.now()
    run.save()
    link.last_replay_at = run.finished_at
    link.save(update_fields=["last_replay_at", "updated_at"])
    services.recompute_failure_rate(link)
    events.stage_failed(link, "replay", "; ".join(str(f) for f in failures)[:200])
    return run
