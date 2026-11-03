from django.urls import path

from catalog.api import PublishedPlansView, RecentCompaniesView, SiteConfigView

urlpatterns = [
    path("site-config", SiteConfigView.as_view(), name="site-config"),
    path("plans", PublishedPlansView.as_view(), name="published-plans"),
    path("companies/recent", RecentCompaniesView.as_view(), name="recent-companies"),
]
