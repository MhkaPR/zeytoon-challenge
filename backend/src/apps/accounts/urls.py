"""Authentication API routes, mounted under /api/v1/auth/."""

from rest_framework.routers import DefaultRouter

from accounts import api

app_name = "accounts"

router = DefaultRouter()
router.register("", api.OtpRequestViewSet, basename="otp-request")
router.register("", api.OtpVerifyViewSet, basename="otp-verify")
router.register("", api.TokenRefreshViewSet, basename="token-refresh")
router.register("", api.SessionViewSet, basename="session")
router.register("", api.LogoutViewSet, basename="logout")

urlpatterns = router.urls
