"""Catalog routes, mounted under /api/v1/catalog/."""

from rest_framework.routers import SimpleRouter

from apps.catalog import api

app_name = "catalog"

router = SimpleRouter(trailing_slash=False)
router.register("", api.SiteConfigViewSet, basename="site-config")
router.register("plans", api.PublishedPlansViewSet, basename="published-plans")
router.register("", api.RecentCompaniesViewSet, basename="recent-companies")

urlpatterns = router.urls
