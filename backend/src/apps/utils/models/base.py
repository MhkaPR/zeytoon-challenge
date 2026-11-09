"""Abstract base model providing timestamps and soft-delete behavior."""

from django.db import models
from django.utils import timezone

from apps.utils.models.soft_delete import (
    DeletedObjectsManager,
    SoftDeleteConflict,
    SoftDeleteManager,
)


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
        for relation in self._meta.related_objects:
            field = relation.field
            if field.null:
                continue
            if field.remote_field.on_delete in (
                models.SET_NULL,
                models.SET_DEFAULT,
                models.DO_NOTHING,
            ):
                continue
            if relation.related_model.objects.filter(
                **{field.name: self}
            ).exists():
                raise SoftDeleteConflict(
                    f"{self._meta.label} is still referenced by "
                    f"{relation.related_model._meta.label}.{field.name}"
                )
        self.deleted_at = timezone.now()
        self.save(using=using, update_fields=("deleted_at", "updated_at"))
        return 1, {self._meta.label: 1}

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)
