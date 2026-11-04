"""LLM token budget and spend rows."""

from django.conf import settings
from django.db import models
from apps.utils.models import TimestampedModel
from apps.admin_console.models.table import ExtractedTable
from apps.admin_console.models.link import Link


class LlmCostLedger(TimestampedModel):
    """Model-backed LLM token budget and spend rows (Principle II, FR-047..FR-050)."""

    class Scope(models.TextChoices):
        GLOBAL = "global", "Global"

    class Period(models.TextChoices):
        DAILY = "daily", "Daily"
        MONTHLY = "monthly", "Monthly"
        TOTAL = "total", "Total"

    class Stage(models.TextChoices):
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
    amount = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
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
    links = models.ManyToManyField(
        Link,
        blank=True,
        related_name="batch_llm_spend_rows",
    )
    table_ref = models.ForeignKey(
        ExtractedTable,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="llm_spend_rows",
    )
    idempotency_key = models.CharField(max_length=255)

    class Meta:
        db_table = "admin_console_llm_cost_ledger"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("idempotency_key",),
                condition=models.Q(deleted_at__isnull=True),
                name="uniq_active_llm_cost_idempotency_key",
            )
        ]

    def __str__(self):
        return f"llm spend {self.stage} ({self.tokens_used} tokens)"
