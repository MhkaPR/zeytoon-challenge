"""Public interface for the pipeline module (Constitution Principle V).

Other modules read pipeline state only through this interface; it exposes opaque ids
and summaries and leaks no internals. The interface is internal to the backend and is
not an HTTP surface (FR-066).
"""

from django.db import transaction

from apps.pipeline.models import CaptureSession, FailureAlert, Link, Site


class TaskBackendUnavailable(RuntimeError):
    """Raised when the configured task backend refuses an enqueue."""


def _require_operator(actor):
    """The pipeline interface is operator-only (FR-066)."""
    if actor is None or not getattr(actor, "is_authenticated", False):
        raise PermissionError("An authenticated operator is required.")
    if not actor.is_operator():
        raise PermissionError("This action is restricted to operators.")
    return actor


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
    def public_link_urls(link_ids):
        """Return the source URL for each published plan link."""
        return {
            link.pk: link.url
            for link in Link.objects.filter(pk__in=link_ids).only("id", "url")
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
    def all_sites():
        return Site.objects.select_related("company").all()

    @staticmethod
    def site_or_error(site_id):
        site = Site.objects.filter(pk=site_id).first()
        if site is None:
            raise LookupError("site_not_found")
        return site

    @staticmethod
    def link_queryset():
        return Link.objects.all()

    @staticmethod
    def link_or_error(link_id):
        link = Link.objects.filter(pk=link_id).first()
        if link is None:
            raise LookupError("link_not_found")
        return link

    @staticmethod
    def capture_session_or_error(session_id):
        session = CaptureSession.objects.filter(pk=session_id).first()
        if session is None:
            raise LookupError("capture_session_not_found")
        return session

    @staticmethod
    def site_links(site, review_state=None):
        qs = site.links.all()
        if review_state:
            qs = qs.filter(review_state=review_state)
        return qs.order_by("-created_at")

    @staticmethod
    def link_capture_sessions(link):
        return link.capture_sessions.all()

    @staticmethod
    def link_plans(link):
        return link.plan_records.all()

    @staticmethod
    def onboard_site(company_id, actor=None):
        _require_operator(actor)
        from apps.pipeline.services.v1.pipeline import onboard_site

        return onboard_site(company_id, actor=actor)

    @staticmethod
    def suspend_site(site, actor=None):
        _require_operator(actor)
        site.maintenance_state = Site.MaintenanceState.SUSPENDED
        site.save(update_fields=["maintenance_state", "updated_at"])
        return site

    @staticmethod
    def resume_site(site, actor=None):
        _require_operator(actor)
        site.maintenance_state = Site.MaintenanceState.ONBOARDING
        site.save(update_fields=["maintenance_state", "updated_at"])
        return site

    @staticmethod
    def enqueue_site_pipeline(
        site_id, actor=None, *, discover=True, link_id=None, priority=None
    ):
        _require_operator(actor)
        from apps.pipeline.tasks import run_site_pipeline_task

        try:
            task = (
                run_site_pipeline_task.using(priority=priority)
                if priority is not None
                else run_site_pipeline_task
            )
            task.enqueue(site_id, discover=discover, link_id=link_id)
        except Exception as exc:  # noqa: BLE001 - backend-specific failure surface
            raise TaskBackendUnavailable("task_backend_unavailable") from exc

    @staticmethod
    def enqueue_replay(link_id, actor=None):
        _require_operator(actor)
        from apps.pipeline.tasks import run_replay_task

        try:
            run_replay_task.enqueue(link_id)
        except Exception as exc:  # noqa: BLE001
            raise TaskBackendUnavailable("task_backend_unavailable") from exc


__all__ = ["PipelineInterface", "TaskBackendUnavailable"]
