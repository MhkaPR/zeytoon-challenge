"""Public interface for the pipeline module (Constitution Principle V).

Other modules read pipeline state only through this interface; it exposes opaque ids
and summaries and leaks no internals. The interface is internal to the backend and is
not an HTTP surface.
"""

from django.db import transaction

from apps.pipeline.models import FailureAlert, Link, Site


class PipelineInterface:
    """The single sanctioned entry point into pipeline state and work."""

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
    def public_site_details(site_ids):
        """Return site identity needed to render the public catalog."""
        return {
            site.pk: {
                "domain": site.domain,
                "company_name": site.company.company_name,
            }
            for site in Site.objects.filter(pk__in=site_ids).select_related("company")
        }

    @staticmethod
    def public_recent_companies(since):
        """Return verified public companies created since the supplied timestamp."""
        return [
            {
                "domain": site.domain,
                "company_name": site.company.company_name,
                "created_at": site.company.created_at,
            }
            for site in Site.objects.filter(
                company__verification_status="verified",
                company__is_archived=False,
                company__created_at__gte=since,
            )
            .select_related("company")
            .order_by("-company__created_at", "company__company_name")[:3]
        ]

    @staticmethod
    def open_alert_count():
        return FailureAlert.objects.filter(state=FailureAlert.State.OPEN).count()

    @staticmethod
    def published_source_id():
        """The provenance ``source`` value console writes into ``catalog`` (FR-037)."""
        return "admin_console"

    @staticmethod
    def site_for_company(company_id):
        return Site.objects.filter(company_id=company_id).first()

    @staticmethod
    def onboard_site(company_id, actor=None):
        from apps.pipeline.services.v1.pipeline import onboard_site

        return onboard_site(company_id, actor=actor)

    @staticmethod
    def suspend_site(site):
        site.maintenance_state = Site.MaintenanceState.SUSPENDED
        site.save(update_fields=["maintenance_state", "updated_at"])
        return site

    @staticmethod
    def resume_site(site):
        site.maintenance_state = Site.MaintenanceState.ONBOARDING
        site.save(update_fields=["maintenance_state", "updated_at"])
        return site

    @staticmethod
    def enqueue_site_pipeline(site_id, *, discover=True, link_id=None):
        from apps.pipeline.tasks import run_site_pipeline_task

        transaction.on_commit(
            lambda: run_site_pipeline_task.enqueue(
                site_id, discover=discover, link_id=link_id
            )
        )

    @staticmethod
    def enqueue_replay(link_id):
        from apps.pipeline.tasks import run_replay_task

        transaction.on_commit(lambda: run_replay_task.enqueue(link_id))


__all__ = ["PipelineInterface"]
