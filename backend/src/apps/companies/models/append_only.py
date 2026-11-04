"""Insert-only mixin for append-only audit records."""

from django.contrib.auth import get_user_model
from django.db import models
from apps.utils.models import TimestampedModel


class _AppendOnlyMixin(models.Model):
    """Mixin making a model insert-only: existing rows cannot be updated or deleted."""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk is not None and type(self).objects.filter(pk=self.pk).exists():
            raise ValueError("This record is append-only and cannot be modified.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("This record is append-only and cannot be deleted.")
