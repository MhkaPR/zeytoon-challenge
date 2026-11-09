"""Shared DRF pagination that emits the project response envelope."""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.utils.serializers import PageMetaSerializer, PaginatedResponseSerializer


class EnvelopePageNumberPagination(PageNumberPagination):
    """Page-number pagination with a hard page-size cap and `{data, page}` envelope."""

    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 12

    def get_paginated_response(self, data, page_extra=None):
        page = PageMetaSerializer(
            {
                "count": self.page.paginator.count,
                "page": self.page.number,
                "page_size": self.page_size,
                "total_pages": self.page.paginator.num_pages,
            }
        ).data
        if page_extra:
            page.update(page_extra)
        return Response(PaginatedResponseSerializer({"data": data, "page": page}).data)


__all__ = ["EnvelopePageNumberPagination"]
