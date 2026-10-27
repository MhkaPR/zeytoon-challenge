"""DRF views for the notifications inbox and recipient management (FR-041).

Mounted under ``/api/v1/ops/`` so the operator console owns the surface. Every view
requires an authenticated operator (admin role); recipients are admin-managed.
"""

from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts import selectors as account_selectors
from accounts.exceptions import ApiError
from notifications import services
from notifications.models import NotificationRecipient
from notifications.serializers import (
    NotificationRecipientInput,
    NotificationSerializer,
    RecipientSerializer,
    parse_input,
)

User = get_user_model()


class _AdminOnlyView(APIView):
    def caller(self, request):
        user = account_selectors.user_from_request(request)
        if user is None:
            raise ApiError(
                "not_authenticated", "Authentication is required.", http_status=401
            )
        if not user.is_admin():
            raise ApiError(
                "admin_required",
                "This action is restricted to operators.",
                http_status=403,
            )
        return user


class NotificationInboxView(_AdminOnlyView):
    """The caller's in-app notification inbox (FR-041)."""

    @extend_schema(responses={200: dict})
    def get(self, request):
        user = self.caller(request)
        notifications = services.inbox_for_user(user)
        return Response(
            {
                "results": [NotificationSerializer(n).data for n in notifications],
                "count": len(notifications),
            }
        )


class NotificationRecipientListCreateView(_AdminOnlyView):
    @extend_schema(request=NotificationRecipientInput, responses={200: dict, 201: dict})
    def get(self, request):
        self.caller(request)
        recipients = list(NotificationRecipient.objects.select_related("user").all())
        return Response(
            {
                "results": [RecipientSerializer(r).data for r in recipients],
                "count": len(recipients),
            }
        )

    @extend_schema(request=NotificationRecipientInput, responses={201: dict, 410: dict})
    def post(self, request):
        actor = self.caller(request)
        payload = parse_input(NotificationRecipientInput, request.data)
        try:
            user = User.objects.get(pk=payload.user_id)
        except User.DoesNotExist:
            raise ApiError(
                "not_found",
                "The target user does not exist.",
                http_status=404,
                fields={"user_id": payload.user_id},
            )
        recipient = services.add_recipient(
            user=user, name=payload.name or "", actor=actor
        )
        return Response(
            RecipientSerializer(recipient).data, status=status.HTTP_201_CREATED
        )


class NotificationRecipientDeactivateView(_AdminOnlyView):
    @extend_schema(request=None, responses={200: dict, 404: dict})
    def post(self, request, recipient_id):
        self.caller(request)
        recipient = NotificationRecipient.objects.filter(pk=recipient_id).first()
        if recipient is None:
            raise ApiError(
                "not_found",
                "The recipient does not exist.",
                http_status=404,
                fields={"recipient_id": recipient_id},
            )
        services.deactivate_recipient(recipient)
        return Response(RecipientSerializer(recipient).data)
