"""Shared abstract model bases for the whole project."""

from django.db import models


class TimestampedModel(models.Model):
    """Abstract base providing audit timestamps to every concrete model."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
