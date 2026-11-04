"""Discovered link under a site."""

from django.conf import settings
from django.db import models
from apps.utils.models import TimestampedModel


class Link(TimestampedModel):
    """A page address within a site: discovery state and pipeline stage."""

    class Source(models.TextChoices):
        ADAPTIVE_CRAWL = "adaptive_crawl", "Adaptive crawl"
        MANUAL = "manual", "Manual"

    class ReviewState(models.TextChoices):
        CANDIDATE = "candidate", "Candidate"
        KEPT = "kept", "Kept"
        DROPPED = "dropped", "Dropped"
        FLAGGED = "flagged", "Flagged"

    class PipelineStage(models.TextChoices):
        DISCOVERED = "discovered", "Discovered"
        CAPTURED = "captured", "Captured"
        EXTRACTED = "extracted", "Extracted"
        PLANS_EXTRACTED = "plans_extracted", "Plans extracted"
        NO_PRICE_TABLES = "no_price_tables", "No price tables found"
        PUBLISHED = "published", "Published"
        AWAITING_LLM_BUDGET = "awaiting_llm_budget", "Awaiting LLM budget"
        FLAGGED = "flagged", "Flagged"
        DEAD_LETTERED = "dead_lettered", "Dead-lettered"

    site = models.ForeignKey("pipeline.Site", on_delete=models.CASCADE, related_name="links")
    url = models.URLField(db_index=True)
    url_hash = models.CharField(max_length=64, db_index=True)
    source = models.CharField(
        max_length=16, choices=Source.choices, default=Source.ADAPTIVE_CRAWL
    )
    review_state = models.CharField(
        max_length=16, choices=ReviewState.choices, default=ReviewState.KEPT
    )
    pipeline_stage = models.CharField(
        max_length=32, choices=PipelineStage.choices, default=PipelineStage.DISCOVERED
    )
    current_trace = models.ForeignKey(
        "pipeline.Trace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_for_links",
    )
    failure_rate = models.FloatField(default=0.0)
    retry_count = models.PositiveIntegerField(default=0)
    last_error = models.CharField(max_length=512, blank=True, default="")
    pipeline_task_state = models.CharField(max_length=16, default="idle", db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    last_replay_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "admin_console_link"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("site", "url_hash"),
                condition=models.Q(deleted_at__isnull=True),
                name="uniq_link_site_url_hash",
            )
        ]

    def __str__(self):
        return self.url
