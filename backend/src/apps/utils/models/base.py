"""Abstract base model providing timestamps and soft-delete behavior."""

from django.db import models
from django.utils import timezone

from apps.utils.models.soft_delete import DeletedObjectsManager, SoftDeleteManager


class TimestampedModel(models.Model):
    """Abstract base providing timestamps and shared soft-delete behavior."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = SoftDeleteManager()
    deleted_objects = DeletedObjectsManager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        if self.deleted_at is not None:
            return 0, {}
        self.deleted_at = timezone.now()
        self.save(using=using, update_fields=("deleted_at", "updated_at"))
        return 1, {self._meta.label: 1}

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)
