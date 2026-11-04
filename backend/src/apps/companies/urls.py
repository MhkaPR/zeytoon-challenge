"""Company routes, mounted under /api/v1/companies/."""

from rest_framework.routers import SimpleRouter

from apps.companies import api

app_name = "companies"

router = SimpleRouter(trailing_slash=False)
router.register("", api.CompanyViewSet, basename="company")

urlpatterns = router.urls
