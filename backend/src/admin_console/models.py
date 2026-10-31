"""Admin console domain models (spec 003 data-model.md).

All models inherit :class:`utils.models.TimestampedModel`. This module owns the
automated site-maintenance pipeline: Site, Link, CaptureSession, Trace metadata,
extracted tables, TableClassification, PlanRecord, SemanticLabel, ReplayRun,
ChangeRecord, FailureAlert, and the LlmCostLedger (token budget + spend). Company
verification itself stays in ``companies`` and is reached only through
``companies.interfaces``.
"""

from django.conf import settings
from django.db import models

from utils.models import TimestampedModel


class Site(TimestampedModel):
    """The single crawl target for an approved company (FR-007).

    The domain is the adaptive-crawl seed; there is no sitemap state.
    """

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
    crawl_query = models.CharField(max_length=512, blank=True, default="")
    maintenance_state = models.CharField(
        max_length=16,
        choices=MaintenanceState.choices,
        default=MaintenanceState.ONBOARDING,
    )
    onboarded_at = models.DateTimeField(null=True, blank=True)
    last_discovered_at = models.DateTimeField(null=True, blank=True)
    last_replay_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "admin_console_site"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.domain} ({self.maintenance_state})"


class Link(TimestampedModel):
    """A page address within a site: discovery state, refilter verdict, stage."""

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
        REFILTERED = "refiltered", "Refiltered"
        CAPTURED = "captured", "Captured"
        EXTRACTED = "extracted", "Extracted"
        CLASSIFIED = "classified", "Classified"
        PLANS_EXTRACTED = "plans_extracted", "Plans extracted"
        PUBLISHED = "published", "Published"
        AWAITING_LLM_BUDGET = "awaiting_llm_budget", "Awaiting LLM budget"
        FLAGGED = "flagged", "Flagged"
        DEAD_LETTERED = "dead_lettered", "Dead-lettered"

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="links")
    url = models.URLField(db_index=True)
    url_hash = models.CharField(max_length=64, db_index=True)
    source = models.CharField(
        max_length=16, choices=Source.choices, default=Source.ADAPTIVE_CRAWL
    )
    review_state = models.CharField(
        max_length=16, choices=ReviewState.choices, default=ReviewState.CANDIDATE
    )
    refilter_plan_type = models.CharField(max_length=64, blank=True, default="")
    refilter_confidence = models.FloatField(null=True, blank=True)
    refilter_flag = models.BooleanField(default=False)
    pipeline_stage = models.CharField(
        max_length=32, choices=PipelineStage.choices, default=PipelineStage.DISCOVERED
    )
    current_trace = models.ForeignKey(
        "admin_console.Trace",
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
                fields=("site", "url_hash"), name="uniq_link_site_url_hash"
            )
        ]

    def __str__(self):
        return self.url


class CaptureSession(TimestampedModel):
    """One server-side headless capture attempt (FR-016..FR-018)."""

    class Mode(models.TextChoices):
        HEADLESS_FIXED = "headless_fixed", "Headless fixed"

    class State(models.TextChoices):
        PENDING = "pending", "Pending"
        RECORDING = "recording", "Recording"
        STORED = "stored", "Stored"
        FAILED = "failed", "Failed"

    NON_TERMINAL = (State.PENDING, State.RECORDING)

    link = models.ForeignKey(
        Link, on_delete=models.CASCADE, related_name="capture_sessions"
    )
    mode = models.CharField(
        max_length=16, choices=Mode.choices, default=Mode.HEADLESS_FIXED
    )
    state = models.CharField(
        max_length=16, choices=State.choices, default=State.PENDING
    )
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
                condition=models.Q(state__in=("pending", "recording")),
                name="uniq_nonterminal_capture_session_per_link",
            ),
        ]

    def __str__(self):
        return f"capture {self.pk} ({self.state})"


class Trace(TimestampedModel):
    """Metadata for a domtrack trace stored as an artifact (FR-000a, FR-019).

    The trace body is never stored in a database column; only the storage key, backend
    alias, byte size, and hash are kept. Capture is server-side, so no operator is
    recorded.
    """

    class Origin(models.TextChoices):
        SERVER_CAPTURE = "server_capture", "Server capture"
        REPLAY_RECORDING = "replay_recording", "Replay recording"

    link = models.ForeignKey(Link, on_delete=models.CASCADE, related_name="traces")
    capture_session = models.ForeignKey(
        CaptureSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="traces",
    )
    captured_at = models.DateTimeField()
    origin = models.CharField(
        max_length=32,
        choices=Origin.choices,
        default=Origin.SERVER_CAPTURE,
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
    """A table document domtrack discovered in a trace (FR-020)."""

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
    """A column of an extracted table; ``path`` is domtrack's selector (diagnostics)."""

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
    """A row of an extracted table; ``cells`` maps column_id -> value (FR-020)."""

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


class TableClassification(TimestampedModel):
    """The LLM verdict for an extracted table (FR-023..FR-025)."""

    table = models.OneToOneField(
        ExtractedTable, on_delete=models.CASCADE, related_name="classification"
    )
    is_plans_table = models.BooleanField(default=False)
    plan_type = models.CharField(max_length=64, blank=True, default="")
    confidence = models.FloatField(default=0.0)
    provider = models.CharField(max_length=64, blank=True, default="")
    model = models.CharField(max_length=128, blank=True, default="")
    prompt_version = models.CharField(max_length=64, blank=True, default="v1")

    class Meta:
        db_table = "admin_console_table_classification"
        ordering = ("-confidence", "id")

    def __str__(self):
        kind = self.plan_type if self.is_plans_table else "not-plans"
        return f"table {self.table_id}: {kind} ({self.confidence:.2f})"


class PlanRecord(TimestampedModel):
    """A normalized plan extracted from a plans table (FR-026..FR-031).

    ``values`` is keyed by schema field key; it contains data only — no selectors and
    no formulas.
    """

    link = models.ForeignKey(Link, on_delete=models.CASCADE, related_name="plan_records")
    table = models.ForeignKey(
        ExtractedTable, on_delete=models.CASCADE, related_name="plan_records"
    )
    classification = models.ForeignKey(
        TableClassification,
        on_delete=models.CASCADE,
        related_name="plan_records",
    )
    plan_type = models.CharField(max_length=64)
    natural_key = models.CharField(max_length=512, db_index=True)
    values = models.JSONField(default=dict, blank=True)
    confidence = models.FloatField(null=True, blank=True)
    prompt_version = models.CharField(max_length=64, blank=True, default="v1")

    class Meta:
        db_table = "admin_console_plan_record"
        ordering = ("id",)
        constraints = [
            models.UniqueConstraint(
                fields=("link", "natural_key"),
                name="uniq_plan_record_link_key",
            )
        ]

    def __str__(self):
        return f"{self.plan_type}:{self.natural_key}"


class PlanExclusion(TimestampedModel):
    """Operator decision to keep a logical plan out across future extractions."""

    link = models.ForeignKey(Link, on_delete=models.CASCADE, related_name="plan_exclusions")
    fingerprint = models.CharField(max_length=64)
    plan_type = models.CharField(max_length=64)
    plan_name = models.CharField(max_length=255)
    price_amount = models.CharField(max_length=64)

    class Meta:
        db_table = "admin_console_plan_exclusion"
        constraints = [
            models.UniqueConstraint(
                fields=("link", "fingerprint"), name="uniq_plan_exclusion_link_fingerprint"
            )
        ]


class SemanticLabel(TimestampedModel):
    """An optional LLM semantic label for a table/column (FR-032..FR-034)."""

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
    label = models.CharField(max_length=512, blank=True, default="")
    provider = models.CharField(max_length=64, blank=True, default="")
    model = models.CharField(max_length=128, blank=True, default="")
    language = models.CharField(max_length=16, blank=True, default="fa")

    class Meta:
        db_table = "admin_console_semantic_label"
        ordering = ("id",)

    def __str__(self):
        return self.label or f"label {self.pk}"


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
    touches_plans_table = models.BooleanField(default=False)
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
        return f"{self.change_kind} (plans={self.touches_plans_table})"


class FailureAlert(TimestampedModel):
    """A link-state alert raised when a link's failure rate crosses threshold (FR-044)."""

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
    """Model-backed LLM token budget and spend rows (Principle II, FR-047..FR-050)."""

    class Scope(models.TextChoices):
        GLOBAL = "global", "Global"

    class Period(models.TextChoices):
        DAILY = "daily", "Daily"
        MONTHLY = "monthly", "Monthly"
        TOTAL = "total", "Total"

    class Stage(models.TextChoices):
        REFILTER = "refilter", "Refilter"
        CLASSIFICATION = "classification", "Classification"
        SCHEMA_EXTRACTION = "schema_extraction", "Schema extraction"
        LABELING = "labeling", "Labeling"

    scope = models.CharField(max_length=128, default=Scope.GLOBAL, db_index=True)
    token_budget = models.BigIntegerField(null=True, blank=True)
    period = models.CharField(
        max_length=16, choices=Period.choices, default=Period.MONTHLY
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="llm_token_budgets",
    )
    timestamp = models.DateTimeField(null=True, blank=True)
    tokens_used = models.BigIntegerField(default=0)
    amount = models.DecimalField(
        max_digits=14, decimal_places=4, null=True, blank=True
    )
    stage = models.CharField(
        max_length=32, choices=Stage.choices, blank=True, default=""
    )
    link_ref = models.ForeignKey(
        Link,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="llm_spend_rows",
    )
    table_ref = models.ForeignKey(
        ExtractedTable,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="llm_spend_rows",
    )
    idempotency_key = models.CharField(max_length=255, unique=True)

    class Meta:
        db_table = "admin_console_llm_cost_ledger"
        ordering = ("-created_at",)

    def __str__(self):
        return f"llm spend {self.stage} ({self.tokens_used} tokens)"
