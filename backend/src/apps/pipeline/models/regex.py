"""Admin-managed classification regexes."""

from django.conf import settings
from django.db import models
from apps.utils.models import TimestampedModel


class ClassificationRegex(TimestampedModel):
    """Admin-managed regex rules used by table classification."""

    class Kind(models.TextChoices):
        KEYWORD = "keyword", "Keyword"
        NUMBER = "number", "Number"

    kind = models.CharField(max_length=24, choices=Kind.choices, db_index=True)
    pattern = models.CharField(max_length=512)
    is_active = models.BooleanField(default=True, db_index=True)
    description = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "admin_console_classification_regex"
        ordering = ("kind", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("pattern",),
                condition=models.Q(deleted_at__isnull=True),
                name="uniq_active_classification_regex_pattern",
            )
        ]

    def clean(self):
        import re

        from django.core.exceptions import ValidationError

        try:
            re.compile(self.pattern, re.IGNORECASE)
        except re.error as exc:
            raise ValidationError(
                {"pattern": f"Invalid regular expression: {exc}"}
            ) from exc

    def __str__(self):
        return f"{self.get_kind_display()}: {self.pattern}"
