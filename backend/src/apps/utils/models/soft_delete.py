"""Soft-delete query set and managers shared by every model."""

from django.db import models
from django.db.models import ProtectedError
from django.utils import timezone


class SoftDeleteConflict(ProtectedError):
    """Raised when a required relationship still references the record."""

    def __init__(self, message):
        self.message = message
        super().__init__(message, [])


class SoftDeleteQuerySet(models.QuerySet):
    """Query set whose ordinary delete operation retains rows for auditability."""

    def delete(self):
        count = self.update(deleted_at=timezone.now())
        return count, {self.model._meta.label: count}

    def hard_delete(self):
        return super().delete()


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    """Default manager returning active rows only."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class DeletedObjectsManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    """Manager for inspecting retained deleted rows."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=False)
