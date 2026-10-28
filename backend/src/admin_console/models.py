"""Admin console domain models (spec 003 data-model.md).

All models inherit :class:`utils.models.TimestampedModel`. This module owns the site
maintenance pipeline: Site, Link, CaptureSession, Trace metadata, extracted tables,
SemanticLabel, ExtractionRecipe/RecipeFieldBinding, ReplayRun, FailureAlert, and
LlmCostLedger. Company verification itself stays in ``companies`` and is reached only
through ``companies.interfaces``.
"""

from django.conf import settings
from django.db import models

from utils.models import TimestampedModel


class Site(TimestampedModel):
    """The single crawl target for an approved company (FR-007)."""

    class MaintenanceState(models.TextChoices):
        ONBOARDING = "onboarding", "Onboarding"
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"

    company = models.OneToOneField(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="ops_site",
    )
    domain = models.CharField(max_length=255, db_index=True)
    has_sitemap = models.BooleanField(default=False)
    sitemap_url = models.URLField(blank=True, default="")
    maintenance_state = models.CharField(
        max_length=16,
        choices=MaintenanceState.choices,
        default=MaintenanceState.ONBOARDING,
    )
    onboarded_at = models.DateTimeField(null=True, blank=True)
    last_replay_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "admin_console_site"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.domain} ({self.maintenance_state})"


class Link(TimestampedModel):
    """A page address within a site, with review state and pipeline stage."""

    class Source(models.TextChoices):
        SITEMAP = "sitemap", "Sitemap"
        MANUAL = "manual", "Manual"

    class ReviewState(models.TextChoices):
        CANDIDATE = "candidate", "Candidate"
        KEPT = "kept", "Kept"
        REMOVED = "removed", "Removed"

    class PipelineStage(models.TextChoices):
        REVIEW = "review", "Review"
        CAPTURE = "capture", "Capture"
        EXTRACTED = "extracted", "Extracted"
        MAPPED = "mapped", "Mapped"
        CLEANED = "cleaned", "Cleaned"
        PUBLISHED = "published", "Published"
        FLAGGED = "flagged", "Flagged"
        FAILED = "failed", "Failed"

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="links")
    url = models.URLField(db_index=True)
    url_hash = models.CharField(max_length=64, db_index=True)
    source = models.CharField(
        max_length=16, choices=Source.choices, default=Source.SITEMAP
    )
    review_state = models.CharField(
        max_length=16, choices=ReviewState.choices, default=ReviewState.CANDIDATE
    )
    pipeline_stage = models.CharField(
        max_length=16, choices=PipelineStage.choices, default=PipelineStage.REVIEW
    )
    current_trace = models.ForeignKey(
        "admin_console.Trace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_for_links",
    )
    failure_rate = models.FloatField(default=0.0)
    is_active = models.BooleanField(default=True, db_index=True)
    last_replay_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "admin_console_link"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("site", "url_hash"), name="uniq_link_site_url_hash"
            )
        ]

    def __str__(self):
        return self.url


class CaptureSession(TimestampedModel):
    """One operator-driven capture attempt (FR-012..FR-017)."""

    class Mode(models.TextChoices):
        INTERACTIVE = "interactive", "Interactive"
        FIXED_DURATION = "fixed_duration", "Fixed duration"

    class State(models.TextChoices):
        PENDING = "pending", "Pending"
        RECORDING = "recording", "Recording"
        AWAITING_UPLOAD = "awaiting_upload", "Awaiting upload"
        STORED = "stored", "Stored"
        FAILED = "failed", "Failed"

    NON_TERMINAL = (State.PENDING, State.RECORDING, State.AWAITING_UPLOAD)

    link = models.ForeignKey(
        Link, on_delete=models.CASCADE, related_name="capture_sessions"
    )
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="capture_sessions",
    )
    mode = models.CharField(
        max_length=16, choices=Mode.choices, default=Mode.INTERACTIVE
    )
    state = models.CharField(
        max_length=16, choices=State.choices, default=State.PENDING
    )
    local_path = models.CharField(max_length=1024, blank=True, default="")
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    error = models.CharField(max_length=512, blank=True, default="")
    trace = models.ForeignKey(
        "admin_console.Trace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="capture_sessions",
    )

    class Meta:
        db_table = "admin_console_capture_session"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("link",),
                condition=models.Q(state__in=("pending", "recording", "awaiting_upload")),
                name="uniq_nonterminal_capture_session_per_link",
            ),
            models.UniqueConstraint(
                fields=("operator",),
                condition=models.Q(state__in=("pending", "recording", "awaiting_upload")),
                name="uniq_nonterminal_capture_session_per_operator",
            )
        ]

    def __str__(self):
        return f"capture {self.pk} ({self.state})"


class Trace(TimestampedModel):
    """Metadata for a domtrack trace stored as an artifact (FR-000a, FR-016).

    The trace body is never stored in a database column; only the storage key, backend
    alias, byte size, and hash are kept.
    """

    class Origin(models.TextChoices):
        OPERATOR_CAPTURE = "operator_capture", "Operator capture"
        REPLAY_RECORDING = "replay_recording", "Replay recording"

    link = models.ForeignKey(Link, on_delete=models.CASCADE, related_name="traces")
    capture_session = models.ForeignKey(
        CaptureSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="traces",
    )
    captured_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="captured_traces",
    )
    captured_at = models.DateTimeField()
    origin = models.CharField(
        max_length=32,
        choices=Origin.choices,
        default=Origin.OPERATOR_CAPTURE,
    )
    storage_key = models.CharField(max_length=512, unique=True)
    storage_backend = models.CharField(max_length=64, default="default")
    byte_size = models.PositiveBigIntegerField(default=0)
    content_sha256 = models.CharField(max_length=64, db_index=True)
    is_valid_trace = models.BooleanField(default=False)

    class Meta:
        db_table = "admin_console_trace"
        ordering = ("-captured_at",)

    def __str__(self):
        return self.storage_key


class ExtractedTable(TimestampedModel):
    """A table document domtrack discovered in a trace (FR-018)."""

    trace = models.ForeignKey(
        Trace, on_delete=models.CASCADE, related_name="extracted_tables"
    )
    link = models.ForeignKey(
        Link, on_delete=models.CASCADE, related_name="extracted_tables"
    )
    table_index = models.PositiveIntegerField(default=0)
    parent = models.CharField(max_length=512, blank=True, default="")
    score = models.FloatField(default=0.0)
    column_count = models.PositiveIntegerField(default=0)
    row_count = models.PositiveIntegerField(default=0)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "admin_console_extracted_table"
        ordering = ("-score", "id")

    def __str__(self):
        return f"table {self.pk} ({self.row_count}x{self.column_count})"


class ExtractedTableColumn(TimestampedModel):
    """A column of an extracted table; ``path`` is domtrack's selector (FR-028)."""

    table = models.ForeignKey(
        ExtractedTable, on_delete=models.CASCADE, related_name="columns"
    )
    column_id = models.CharField(max_length=128)
    label = models.CharField(max_length=512, blank=True, default="")
    path = models.CharField(max_length=1024, db_index=True)
    atype = models.CharField(max_length=64, blank=True, default="")
    slot = models.CharField(max_length=64, blank=True, default="")
    coverage = models.FloatField(default=0.0)
    row_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "admin_console_extracted_column"
        ordering = ("id",)

    def __str__(self):
        return f"{self.column_id}: {self.path}"


class ExtractedTableRow(TimestampedModel):
    """A row of an extracted table; ``cells`` maps column_id -> value (FR-018)."""

    table = models.ForeignKey(
        ExtractedTable, on_delete=models.CASCADE, related_name="rows"
    )
    row_index = models.PositiveIntegerField()
    cells = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "admin_console_extracted_row"
        ordering = ("row_index",)
        constraints = [
            models.UniqueConstraint(
                fields=("table", "row_index"),
                name="uniq_extracted_row_table_index",
            )
        ]


class SemanticLabel(TimestampedModel):
    """An LLM semantic label for an extracted table/column (FR-021..FR-024)."""

    table = models.ForeignKey(
        ExtractedTable, on_delete=models.CASCADE, related_name="semantic_labels"
    )
    column = models.ForeignKey(
        ExtractedTableColumn,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="semantic_labels",
    )
    table_title = models.CharField(max_length=512, blank=True, default="")
    table_purpose = models.TextField(blank=True, default="")
    label = models.CharField(max_length=512, blank=True, default="")
    provider = models.CharField(max_length=64, blank=True, default="")
    model = models.CharField(max_length=128, blank=True, default="")

    class Meta:
        db_table = "admin_console_semantic_label"
        ordering = ("id",)

    def __str__(self):
        return self.label or f"label {self.pk}"


class ExtractionRecipe(TimestampedModel):
    """The extraction recipe for a link: schema field bindings (FR-025..FR-031)."""

    link = models.ForeignKey(
        Link, on_delete=models.CASCADE, related_name="recipes"
    )
    plan_type = models.CharField(max_length=64)
    version = models.PositiveIntegerField(default=1)
    is_current = models.BooleanField(default=True, db_index=True)
    is_complete = models.BooleanField(default=False)

    class Meta:
        db_table = "admin_console_extraction_recipe"
        ordering = ("-version",)

    def __str__(self):
        return f"recipe {self.link_id} v{self.version} ({self.plan_type})"


class RecipeFieldBinding(TimestampedModel):
    """A binding from one plan-schema field to a source column + formula (FR-028)."""

    recipe = models.ForeignKey(
        ExtractionRecipe, on_delete=models.CASCADE, related_name="bindings"
    )
    schema_field_key = models.CharField(max_length=64)
    source_table = models.ForeignKey(
        ExtractedTable, on_delete=models.CASCADE, null=True, blank=True
    )
    source_column = models.ForeignKey(
        ExtractedTableColumn,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recipe_bindings",
    )
    selector = models.CharField(max_length=1024, blank=True, default="")
    formula = models.CharField(max_length=1024, blank=True, default="")
    aggregation = models.CharField(max_length=32, blank=True, default="")

    class Meta:
        db_table = "admin_console_recipe_binding"
        ordering = ("id",)
        constraints = [
            models.UniqueConstraint(
                fields=("recipe", "schema_field_key"),
                name="uniq_recipe_field_key",
            )
        ]

    def __str__(self):
        return f"{self.schema_field_key} -> {self.selector}"


class ReplayRun(TimestampedModel):
    """A scheduled domtrack replay of a link (FR-037..FR-039)."""

    class State(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    link = models.ForeignKey(Link, on_delete=models.CASCADE, related_name="replay_runs")
    recipe = models.ForeignKey(
        ExtractionRecipe,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replay_runs",
    )
    scheduled_for = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    state = models.CharField(
        max_length=16, choices=State.choices, default=State.SCHEDULED
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
    diff_applied = models.BooleanField(default=False)
    stats_applied = models.PositiveIntegerField(default=0)
    stats_skipped = models.PositiveIntegerField(default=0)
    stats_failed = models.PositiveIntegerField(default=0)
    failures = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "admin_console_replay_run"
        ordering = ("-created_at",)

    def __str__(self):
        return f"replay {self.pk} ({self.state})"


class FailureAlert(TimestampedModel):
    """A link-state alert raised when a link's failure rate crosses threshold (FR-040)."""

    class State(models.TextChoices):
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Resolved"

    link = models.ForeignKey(
        Link, on_delete=models.CASCADE, related_name="failure_alerts"
    )
    state = models.CharField(max_length=16, choices=State.choices, default=State.OPEN)
    failure_rate = models.FloatField(default=0.0)
    raised_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    notification_dedup_key = models.CharField(
        max_length=255, blank=True, default="", db_index=True
    )

    class Meta:
        db_table = "admin_console_failure_alert"
        ordering = ("-created_at",)

    def __str__(self):
        return f"alert {self.pk} ({self.state})"


class LlmCostLedger(TimestampedModel):
    """Model-backed LLM cost ceiling and spend rows (Principle II, FR-024)."""

    class Scope(models.TextChoices):
        GLOBAL = "global", "Global"

    class Period(models.TextChoices):
        DAILY = "daily", "Daily"
        MONTHLY = "monthly", "Monthly"
        TOTAL = "total", "Total"

    scope = models.CharField(max_length=128, default=Scope.GLOBAL, db_index=True)
    ceiling_amount = models.DecimalField(
        max_digits=14, decimal_places=4, null=True, blank=True
    )
    period = models.CharField(
        max_length=16, choices=Period.choices, default=Period.MONTHLY
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="llm_cost_ceilings",
    )
    timestamp = models.DateTimeField(null=True, blank=True)
    amount = models.DecimalField(
        max_digits=14, decimal_places=4, null=True, blank=True
    )
    label_run_ref = models.ForeignKey(
        Link,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="llm_cost_rows",
    )

    class Meta:
        db_table = "admin_console_llm_cost_ledger"
        ordering = ("-created_at",)

    def __str__(self):
        return f"llm cost {self.scope} ({self.period})"
