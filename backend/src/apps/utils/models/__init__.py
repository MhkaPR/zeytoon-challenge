"""Shared model base classes for the whole project."""

from apps.utils.models.base import TimestampedModel
from apps.utils.models.soft_delete import (
    DeletedObjectsManager,
    SoftDeleteManager,
    SoftDeleteQuerySet,
)

__all__ = [
    "TimestampedModel",
    "SoftDeleteManager",
    "DeletedObjectsManager",
    "SoftDeleteQuerySet",
]
