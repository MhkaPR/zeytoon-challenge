"""Shared DRF serializer helpers."""

from rest_framework import serializers


def parse_input(serializer_cls, data, *, code="invalid_field", message=None):
    """Validate ``data`` with a DRF serializer, raising ``ApiError`` on failure.

    Returns ``serializer.validated_data`` so views work with validated, typed input.
    """
    from apps.accounts.exceptions import ApiError

    serializer = serializer_cls(data=data)
    if not serializer.is_valid():
        raise ApiError(
            code,
            message or "Some fields are missing or invalid.",
            fields={"fields": list(serializer.errors.keys())},
        )
    return serializer.validated_data


class PageMetaSerializer(serializers.Serializer):
    """Pagination metadata shared by every paginated list response."""

    count = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total_pages = serializers.IntegerField()


class PaginatedResponseSerializer(serializers.Serializer):
    """Shared `{data, page}` envelope for every paginated list response."""

    data = serializers.ListField(child=serializers.JSONField())
    page = serializers.DictField()


__all__ = [
    "PageMetaSerializer",
    "PaginatedResponseSerializer",
    "parse_input",
    "serializers",
]
