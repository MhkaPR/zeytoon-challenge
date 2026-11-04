"""DRF views for the notifications inbox and recipient management (FR-041).

Mounted under ``/api/v1/ops/`` so the operator console owns the surface. Every view
requires an authenticated operator (admin role); recipients are admin-managed.
"""

from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, ListModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.accounts import selectors as account_selectors
from apps.accounts.exceptions import ApiError
from apps.notifications import services
from apps.notifications.models import NotificationRecipient
from apps.notifications.serializers import (
    NotificationInboxSerializer,
    NotificationRecipientInputSerializer,
    RecipientListSerializer,
    RecipientSerializer,
    parse_input,
)

User = get_user_model()


class AdminOnlyViewSet(GenericViewSet):
    """Base viewset resolving the caller and requiring an operator."""

    def caller(self, request):
        user = account_selectors.user_from_request(request)
        if user is None:
            raise ApiError(
                "not_authenticated", "Authentication is required.", http_status=401
            )
        if not user.is_operator():
            raise ApiError(
                "admin_required",
                "This action is restricted to operators.",
                http_status=403,
            )
        return user


class NotificationInboxViewSet(AdminOnlyViewSet):
    """The caller's in-app notification inbox (FR-041)."""

    @extend_schema(responses={200: dict})
    @action(detail=False, methods=["get"], url_path="notifications")
    def inbox(self, request):
        user = self.caller(request)
        notifications = services.inbox_for_user(user)
        return Response(
            NotificationInboxSerializer(
                {"results": notifications, "count": len(notifications)}
            ).data
        )


class NotificationRecipientViewSet(
    ListModelMixin, CreateModelMixin, AdminOnlyViewSet
):
    queryset = NotificationRecipient.objects.select_related("user").all()

    @extend_schema(
        request=NotificationRecipientInputSerializer, responses={200: dict, 201: dict}
    )
    def list(self, request, *args, **kwargs):
        self.caller(request)
        recipients = list(self.get_queryset())
        return Response(
            RecipientListSerializer(
                {"results": recipients, "count": len(recipients)}
            ).data
        )

    @extend_schema(
        request=NotificationRecipientInputSerializer, responses={201: dict, 410: dict}
    )
    def create(self, request, *args, **kwargs):
        actor = self.caller(request)
        payload = parse_input(NotificationRecipientInputSerializer, request.data)
        try:
            user = User.objects.get(pk=payload["user_id"])
        except User.DoesNotExist:
            raise ApiError(
                "not_found",
                "The target user does not exist.",
                http_status=404,
                fields={"user_id": payload["user_id"]},
            )
        recipient = services.add_recipient(
            user=user, name=payload.get("name") or "", actor=actor
        )
        return Response(
            RecipientSerializer(recipient).data, status=status.HTTP_201_CREATED
        )

    @extend_schema(request=None, responses={200: dict, 404: dict})
    @action(
        detail=True,
        methods=["post"],
        url_path="deactivate",
        url_name="deactivate",
    )
    def deactivate(self, request, pk=None):
        self.caller(request)
        recipient = self.get_queryset().filter(pk=pk).first()
        if recipient is None:
            raise ApiError(
                "not_found",
                "The recipient does not exist.",
                http_status=404,
                fields={"recipient_id": pk},
            )
        services.deactivate_recipient(recipient)
        return Response(RecipientSerializer(recipient).data)
