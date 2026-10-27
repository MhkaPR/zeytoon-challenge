"""Public interface for the admin console module (Constitution Principle V).

Other modules (catalog, search, notifications producers) read console-owned state only
through this interface; it exposes opaque ids and summaries and leaks no internals.
"""

from admin_console.models import FailureAlert, Link, Site


class AdminConsoleInterface:
    """The single sanctioned read entry point into the admin console."""

    @staticmethod
    def link_summary(link_id):
        link = Link.objects.select_related("site").filter(pk=link_id).first()
        if link is None:
            return None
        return {
            "id": link.pk,
            "url": link.url,
            "site_id": link.site_id,
            "site_domain": link.site.domain,
            "pipeline_stage": link.pipeline_stage,
            "failure_rate": link.failure_rate,
            "is_active": link.is_active,
        }

    @staticmethod
    def site_summary(site_id):
        site = Site.objects.filter(pk=site_id).first()
        if site is None:
            return None
        return {
            "id": site.pk,
            "domain": site.domain,
            "company_id": site.company_id,
            "maintenance_state": site.maintenance_state,
        }

    @staticmethod
    def open_alert_count():
        return FailureAlert.objects.filter(state=FailureAlert.State.OPEN).count()

    @staticmethod
    def published_source_id():
        """The provenance ``source`` value console writes into ``catalog`` (FR-035)."""
        return "admin_console"


__all__ = ["AdminConsoleInterface"]
