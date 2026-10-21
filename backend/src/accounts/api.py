"""DRF views for the authentication API (see contracts/auth-api.md)."""

from django.conf import settings
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts import selectors, services
from accounts.exceptions import ApiError
from accounts.serializers import OtpRequestInput, OtpVerifyInput, parse_input
from accounts.throttles import (
    OtpRequestPhoneThrottle,
    OtpSourceThrottle,
    OtpVerifyPhoneThrottle,
)
from utils.logging import mask_phone

REFRESH_COOKIE_NAME = "refresh_token"


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


class OtpRequestView(APIView):
    authentication_classes = []
    throttle_classes = [OtpRequestPhoneThrottle, OtpSourceThrottle]

    def post(self, request):
        payload = parse_input(OtpRequestInput, request.data)
        result = services.request_otp(payload.phone_number)
        response = Response(result, status=status.HTTP_200_OK)
        get_token(request)  # ensure the CSRF cookie is present for the frontend
        return response


class OtpVerifyView(APIView):
    authentication_classes = []
    throttle_classes = [OtpVerifyPhoneThrottle, OtpSourceThrottle]

    def post(self, request):
        payload = parse_input(OtpVerifyInput, request.data)
        result = services.verify_otp(
            payload.phone_number, payload.code, return_url=payload.return_url
        )
        user = result["user"]
        body = {
            "access_token": result["tokens"]["access_token"],
            "token_type": "Bearer",
            "expires_in": result["tokens"]["expires_in"],
            "redirect_to": result["redirect_to"],
            "user": {"phone_masked": mask_phone(user.phone_number), "role": user.role()},
        }
        response = Response(body, status=status.HTTP_200_OK)
        return _set_refresh_cookie(response, result["tokens"]["refresh_token"])


class TokenRefreshView(APIView):
    authentication_classes = []
    throttle_classes = [OtpSourceThrottle]

    def post(self, request):
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

        body = {
            "access_token": access,
            "token_type": "Bearer",
            "expires_in": int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
        }
        response = Response(body, status=status.HTTP_200_OK)
        return _set_refresh_cookie(response, str(refresh))


class LogoutView(APIView):
    authentication_classes = []

    def post(self, request):
        raw = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if raw:
            services.revoke_tokens(raw)
        response = Response({"status": "ok"}, status=status.HTTP_200_OK)
        response.delete_cookie(REFRESH_COOKIE_NAME, path="/api/v1/auth/")
        return response


class SessionView(APIView):
    authentication_classes = []

    def get(self, request):
        return Response(selectors.resolve_current_user(request))
