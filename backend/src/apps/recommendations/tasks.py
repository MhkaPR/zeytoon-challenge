"""Scheduled recommendation-space refresh (Django Tasks only)."""

import logging

from django.tasks import task

logger = logging.getLogger(__name__)


@task
def refresh_plan_space_task():
    """Recalculate the semantic plan space and cache it under its version key."""
    from apps.catalog.interfaces import CatalogInterface
    from apps.recommendations.services.v1.store import PlanSpaceProvider

    records = CatalogInterface.published_plan_records()
    logger.info(
        "recommendation_space_refresh_started",
        extra={"event": "recommendation_space_refresh_started", "plan_count": len(records)},
    )
    try:
        bundle = PlanSpaceProvider().refresh(records)
    except Exception:
        logger.exception(
            "recommendation_space_refresh_failed",
            extra={"event": "recommendation_space_refresh_failed", "plan_count": len(records)},
        )
        raise
    logger.info(
        "recommendation_space_refresh_succeeded",
        extra={
            "event": "recommendation_space_refresh_succeeded",
            "version": bundle["version"],
            "plan_count": len(records),
            "dimensions": bundle["values"].shape[1],
        },
    )
    return {"version": bundle["version"], "plans": len(records)}
