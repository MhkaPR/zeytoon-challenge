"""DRF views for the authentication API (see contracts/auth-api.md)."""

from constance import config
from django.conf import settings
from django.middleware.csrf import get_token
from django_ratelimit.core import get_usage
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.accounts import selectors, services
from apps.accounts.exceptions import ApiError
from apps.accounts.serializers import (
    ErrorSerializer,
    OtpRequestResponseSerializer,
    OtpRequestSerializer,
    OtpVerifyResponseSerializer,
    OtpVerifySerializer,
    SessionResponseSerializer,
    StatusSerializer,
    TokenRefreshResponseSerializer,
    parse_input,
)
from apps.accounts.throttles import (
    OtpSourceThrottle,
    OtpVerifyPhoneThrottle,
)
from apps.accounts.validation import normalize_phone

REFRESH_COOKIE_NAME = "refresh_token"


def _mask_phone(phone):
    """Hide the middle digits in API responses."""
    if not phone or len(phone) < 7:
        return "***"
    return f"{phone[:6]}***{phone[-4:]}"


def _set_refresh_cookie(response, refresh_token):
    max_age = int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=max_age,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Strict",
        path="/api/v1/auth/",
    )
    return response


def _otp_phone_rate_key(group, request):
    """Return the validated JSON phone number as django-ratelimit's key."""
    return normalize_phone(request.data.get("phone_number", "")) or "invalid"


class OtpRequestViewSet(GenericViewSet):
    authentication_classes = []
    throttle_classes = [OtpSourceThrottle]

    @extend_schema(
        request=OtpRequestSerializer,
        responses={200: OtpRequestResponseSerializer, 400: ErrorSerializer},
    )
    @action(detail=False, methods=["post"], url_path="otp/request")
    def otp_request(self, request):
        payload = parse_input(OtpRequestSerializer, request.data)
        cooldown = get_usage(
            request,
            group="otp_request_cooldown",
            key=_otp_phone_rate_key,
            rate=f"1/{max(int(config.REQUEST_COOLDOWN_SECONDS), 1)}s",
            method="POST",
            increment=True,
        )
        hourly = get_usage(
            request,
            group="otp_request_hourly",
            key=_otp_phone_rate_key,
            rate=f"{max(int(config.REQUEST_HOURLY_CAP), 1)}/h",
            method="POST",
            increment=True,
        )
        limited = next(
            (
                usage
                for usage in (cooldown, hourly)
                if usage and usage["should_limit"]
            ),
            None,
        )
        if limited:
            retry_after = max(int(limited["time_left"]), 1)
            raise ApiError(
                "rate_limited",
                f"Please wait {retry_after} seconds before requesting another code.",
                http_status=429,
                fields={"retry_after_seconds": retry_after},
            )
        result = services.request_otp(payload["phone_number"])
        response = Response(
            OtpRequestResponseSerializer(result).data, status=status.HTTP_200_OK
        )
        get_token(request)  # ensure the CSRF cookie is present for the frontend
        return response


class OtpVerifyViewSet(GenericViewSet):
    authentication_classes = []
    throttle_classes = [OtpVerifyPhoneThrottle, OtpSourceThrottle]

    @extend_schema(
        request=OtpVerifySerializer,
        responses={200: OtpVerifyResponseSerializer, 400: ErrorSerializer},
    )
    @action(detail=False, methods=["post"], url_path="otp/verify")
    def otp_verify(self, request):
        payload = parse_input(OtpVerifySerializer, request.data)
        result = services.verify_otp(
            payload["phone_number"],
            payload["code"],
            return_url=payload.get("return_url"),
            visitor_id=request.COOKIES.get("visitor_id"),
        )
        user = result["user"]
        body = OtpVerifyResponseSerializer(
            {
                "access_token": result["tokens"]["access_token"],
                "token_type": "Bearer",
                "expires_in": result["tokens"]["expires_in"],
                "redirect_to": result["redirect_to"],
                "user": {"phone": _mask_phone(user.phone_number), "role": user.role()},
            }
        ).data
        response = Response(body, status=status.HTTP_200_OK)
        return _set_refresh_cookie(response, result["tokens"]["refresh_token"])


class TokenRefreshViewSet(GenericViewSet):
    # A token refresh is NOT an OTP action: it must not consume the per-source OTP budget,
    # because the frontend refreshes on every page load. It still falls under the global
    # anon/user limits, which is plenty for abuse protection (FR-019 covers OTP only).
    authentication_classes = []

    @extend_schema(request=None, responses={200: TokenRefreshResponseSerializer})
    @action(detail=False, methods=["post"], url_path="token/refresh")
    def token_refresh(self, request):
        from rest_framework_simplejwt.exceptions import TokenError
        from rest_framework_simplejwt.tokens import RefreshToken

        raw = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if not raw:
            raise ApiError("invalid_token", "The refresh token is missing.", 401)
        try:
            refresh = RefreshToken(raw)
            access = str(refresh.access_token)
            user_id = refresh.get("user_id")
            if settings.SIMPLE_JWT.get("ROTATE_REFRESH_TOKENS"):
                refresh.blacklist()
                from django.contrib.auth import get_user_model

                user = get_user_model().objects.filter(pk=user_id).first()
                if user is None or user.is_blocked:
                    raise ApiError("user_blocked", services.BLOCKED_MESSAGE, 409)
                refresh = RefreshToken.for_user(user)
        except ApiError:
            raise
        except TokenError:
            raise ApiError("invalid_token", "The refresh token is invalid.", 401)

        body = TokenRefreshResponseSerializer(
            {
                "access_token": access,
                "token_type": "Bearer",
                "expires_in": int(
                    settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()
                ),
            }
        ).data
        response = Response(body, status=status.HTTP_200_OK)
        return _set_refresh_cookie(response, str(refresh))


class SessionViewSet(GenericViewSet):
    authentication_classes = []

    @extend_schema(responses={200: SessionResponseSerializer})
    @action(detail=False, methods=["get"], url_path="session")
    def session(self, request):
        return Response(
            SessionResponseSerializer(selectors.resolve_current_user(request)).data
        )


class LogoutViewSet(GenericViewSet):
    authentication_classes = []

    @extend_schema(request=None, responses={200: StatusSerializer})
    @action(detail=False, methods=["post"], url_path="logout")
    def logout(self, request):
        raw = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if raw:
            services.revoke_tokens(raw)
        visitor_id = request.COOKIES.get("visitor_id")
        if visitor_id:
            from apps.recommendations.interfaces import RecommendationsInterface

            RecommendationsInterface.clear_visitor(visitor_id)
        response = Response(
            StatusSerializer({"status": "ok"}).data, status=status.HTTP_200_OK
        )
        response.delete_cookie(REFRESH_COOKIE_NAME, path="/api/v1/auth/")
        response.delete_cookie("visitor_id", path="/")
        return response
