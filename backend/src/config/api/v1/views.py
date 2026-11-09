"""Cross-application API views."""

from rest_framework import status, viewsets
from rest_framework.response import Response


class HealthViewSet(viewsets.ViewSet):
    """Minimal service health endpoint."""

    authentication_classes = []
    permission_classes = []

    def list(self, request):
        return Response({"data": {"status": "ok"}}, status=status.HTTP_200_OK)
