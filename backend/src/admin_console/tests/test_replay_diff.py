"""Replay/diff contract tests (US8, FR-037..FR-039, SC-012)."""

import pytest

from admin_console.models import ReplayRun
from admin_console.tests.factories import make_trace_bytes
from catalog.models import PublishedRecord

pytestmark = pytest.mark.django_db


class _Stats:
    def __init__(self, applied=0, skipped=0, failed=0, failures=None):
        self.applied = applied
        self.skipped = skipped
        self.failed = failed
        self.failures = failures or []


class _Diff:
    def __init__(self, removed=None):
        self.added = []
        self.removed = removed or []
        self.changed = []

    @property
    def summary(self):
        return {
            "a_nodes": 1,
            "b_nodes": 1,
            "added": len(self.added),
            "removed": len(self.removed),
            "changed": len(self.changed),
        }


class _CompareResult:
    def __init__(self, after_path, diff=None, stats=None):
        self.after_path = after_path
        self.diff = diff or _Diff()
        self.stats = stats or _Stats(applied=5)


def _fake_compare(monkeypatch, rows=None, stats=None, diff=None):
    from admin_console import domtrack_client

    def _compare(before_path, replay_config, recording):
        import os

        out_dir = recording.get("output_dir", "/tmp")
        after_path = os.path.join(out_dir, "after.json")
        with open(after_path, "wb") as handle:
            handle.write(make_trace_bytes(rows=rows))
        return _CompareResult(after_path, diff=diff, stats=stats)

    monkeypatch.setattr(domtrack_client, "compare_replay", _compare)


def test_replay_run_records_traces_and_applies_diff(
    operator_client, published_link, monkeypatch
):
    _fake_compare(monkeypatch)
    response = operator_client.post(
        "/api/v1/ops/replay-runs/create",
        {"link_ids": [published_link.pk]},
        format="json",
    )
    assert response.status_code == 201
    result = response.json()["results"][0]
    assert result["diff_applied"] is True

    run = ReplayRun.objects.get(link=published_link)
    assert run.state == ReplayRun.State.SUCCEEDED
    assert run.before_trace_id is not None
    assert run.after_trace_id is not None
    assert run.diff_summary
    assert run.stats_applied == 5
    assert PublishedRecord.objects.filter(
        link=published_link.pk, is_published=True
    ).exists()


def test_replay_run_listing(operator_client, published_link, monkeypatch):
    _fake_compare(monkeypatch)
    operator_client.post(
        "/api/v1/ops/replay-runs/create",
        {"link_ids": [published_link.pk]},
        format="json",
    )
    response = operator_client.get(
        f"/api/v1/ops/replay-runs?link_id={published_link.pk}"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["results"][0]["before_trace_id"] is not None
    assert body["results"][0]["after_trace_id"] is not None


def test_link_failure_endpoint_reports_rate_and_runs(
    operator_client, published_link, monkeypatch
):
    _fake_compare(monkeypatch, stats=_Stats(applied=9, failed=1))
    operator_client.post(
        "/api/v1/ops/replay-runs/create",
        {"link_ids": [published_link.pk]},
        format="json",
    )
    response = operator_client.get(f"/api/v1/ops/links/{published_link.pk}/failure")
    assert response.status_code == 200
    body = response.json()
    assert body["link_id"] == published_link.pk
    assert body["recent_runs"]
    assert body["failure_rate"] == pytest.approx(0.1)
