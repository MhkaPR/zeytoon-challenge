"""US10 — replay compare, content/structural changes, conditional re-extraction (FR-039..FR-043)."""

import pytest

from admin_console.models import ChangeRecord, ReplayRun
from admin_console.replay import execute_replay_run
from admin_console.tests import factories

pytestmark = pytest.mark.django_db

PLANS_PATH = "table > tr > td.col-0"
OTHER_PATH = "body > div > p"


class FakeChange:
    def __init__(self, path, text_changed=True):
        self.path = path
        self.text_changed = text_changed


class FakeDiff:
    def __init__(self, added=(), removed=(), changed=()):
        self.added = list(added)
        self.removed = list(removed)
        self.changed = list(changed)


class FakeCompareResult:
    def __init__(self, after_path, diff, summary):
        self.after_path = after_path
        self.diff = diff
        self.summary = summary


def _compare_result(tmp_path, diff, summary=None):
    after = tmp_path / "after.json"
    after.write_bytes(factories.make_trace_bytes())
    return FakeCompareResult(str(after), diff, summary or {"changed": 1})


def test_change_touching_a_plans_table_reextracts(planned_link, stub_domtrack, tmp_path):
    stub_domtrack.compare_result = _compare_result(
        tmp_path, FakeDiff(changed=[FakeChange(PLANS_PATH)])
    )

    run = execute_replay_run(planned_link)

    assert run.state == ReplayRun.State.SUCCEEDED
    assert run.reextracted is True
    assert run.after_trace_id is not None
    change = ChangeRecord.objects.get(replay_run=run)
    assert change.change_kind == ChangeRecord.Kind.CONTENT
    assert change.touches_plans_table is True


def test_change_elsewhere_runs_no_llm_work(planned_link, stub_domtrack, tmp_path):
    stub_domtrack.compare_result = _compare_result(
        tmp_path, FakeDiff(changed=[FakeChange(OTHER_PATH)])
    )

    run = execute_replay_run(planned_link)

    assert run.state == ReplayRun.State.SUCCEEDED
    assert run.reextracted is False
    change = ChangeRecord.objects.get(replay_run=run)
    assert change.touches_plans_table is False


def test_structural_change_rediscovers_and_reclassifies(planned_link, stub_domtrack,
                                                        stub_llm, tmp_path):
    stub_domtrack.compare_result = _compare_result(
        tmp_path, FakeDiff(added=[(PLANS_PATH, {"tag": "td"})])
    )

    run = execute_replay_run(planned_link)

    assert run.state == ReplayRun.State.SUCCEEDED
    change = ChangeRecord.objects.get(replay_run=run)
    assert change.change_kind == ChangeRecord.Kind.STRUCTURAL
    assert change.touches_plans_table is True
    assert run.reextracted is True
    # A structural change re-ran table discovery + labeling before extraction.
    assert stub_domtrack.extract_calls
    assert stub_domtrack.label_calls
    assert stub_llm.combined_classification_calls


def test_replay_without_a_before_trace_fails(kept_link):
    run = execute_replay_run(kept_link)
    assert run.state == ReplayRun.State.FAILED
    assert run.diff_summary["error"] == "no_before_trace"


def test_compare_failure_is_recorded(planned_link, stub_domtrack, tmp_path):
    stub_domtrack.compare_error = RuntimeError("replay crashed")

    run = execute_replay_run(planned_link)

    assert run.state == ReplayRun.State.FAILED
    assert "replay crashed" in run.failures[0]
