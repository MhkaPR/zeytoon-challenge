"""Recommendation routes, mounted under /api/v1/recommendations/."""

from rest_framework.routers import SimpleRouter

from apps.recommendations.views.v1 import signals

app_name = "recommendations"

router = SimpleRouter(trailing_slash=False)
router.register("signals", signals.SignalViewSet, basename="recommendation-signals")

urlpatterns = router.urls
