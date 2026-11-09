"""Shared viewset base classes."""

from rest_framework.mixins import ListModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.utils.pagination import EnvelopePageNumberPagination


class EnvelopeListViewSet(ListModelMixin, GenericViewSet):
    """List-only viewset that paginates with Django's paginator.

    Pagination and the response envelope live here once so domain viewsets only
    declare their queryset/serializer and, when needed, override the small
    ``serialize_page`` / ``get_page_extra`` hooks.
    """

    pagination_class = EnvelopePageNumberPagination

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        instances = page if page is not None else queryset
        data = self.serialize_page(instances)
        if page is None:
            return Response(data)
        return self.paginator.get_paginated_response(
            data, page_extra=self.get_page_extra()
        )

    def serialize_page(self, instances):
        """Serialize the current page. Override for domain-specific enrichment."""
        return self.get_serializer(instances, many=True).data

    def get_page_extra(self):
        """Extra metadata merged into the `page` object of the envelope."""
        return None


__all__ = ["EnvelopeListViewSet"]
