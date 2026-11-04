"""Replay runs and change records."""

from django.conf import settings
from django.db import models
from apps.utils.models import TimestampedModel
from apps.admin_console.models.link import Link
from apps.admin_console.models.replay import ReplayRun
from apps.admin_console.models.classification import TableClassification
from apps.admin_console.models.trace import Trace


class ReplayRun(TimestampedModel):
    """A scheduled domtrack compare (replay + record + diff) of a link (FR-039..FR-043)."""

    class State(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        AWAITING_LLM_BUDGET = "awaiting_llm_budget", "Awaiting LLM budget"

    link = models.ForeignKey(Link, on_delete=models.CASCADE, related_name="replay_runs")
    scheduled_for = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    state = models.CharField(
        max_length=24, choices=State.choices, default=State.SCHEDULED
    )
    before_trace = models.ForeignKey(
        Trace,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replay_runs_before",
    )
    after_trace = models.ForeignKey(
        Trace,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replay_runs_after",
    )
    diff_summary = models.JSONField(default=dict, blank=True)
    reextracted = models.BooleanField(default=False)
    stats_applied = models.PositiveIntegerField(default=0)
    stats_skipped = models.PositiveIntegerField(default=0)
    stats_failed = models.PositiveIntegerField(default=0)
    failures = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "admin_console_replay_run"
        ordering = ("-created_at",)

    def __str__(self):
        return f"replay {self.pk} ({self.state})"


class ChangeRecord(TimestampedModel):
    """One detected change in a replay, classified content vs structural (FR-041)."""

    class Kind(models.TextChoices):
        CONTENT = "content", "Content"
        STRUCTURAL = "structural", "Structural"

    replay_run = models.ForeignKey(
        ReplayRun, on_delete=models.CASCADE, related_name="changes"
    )
    change_kind = models.CharField(max_length=16, choices=Kind.choices)
    touches_price_table = models.BooleanField(default=False)
    classification = models.ForeignKey(
        TableClassification,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="changes",
    )
    summary = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "admin_console_change_record"
        ordering = ("id",)

    def __str__(self):
        return f"{self.change_kind} (price_table={self.touches_price_table})"
