"""Authentication API routes, mounted under /api/v1/auth/."""

from django.urls import path

from accounts import api

app_name = "accounts"

urlpatterns = [
    path("otp/request", api.OtpRequestView.as_view(), name="otp-request"),
    path("otp/verify", api.OtpVerifyView.as_view(), name="otp-verify"),
    path("token/refresh", api.TokenRefreshView.as_view(), name="token-refresh"),
    path("logout", api.LogoutView.as_view(), name="logout"),
    path("session", api.SessionView.as_view(), name="session"),
]
