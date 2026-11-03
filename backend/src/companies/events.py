"""Structured domain-event logging for the companies feature (FR-046).

The company phone number is emitted as-is; codes and tokens are still redacted by
:mod:`utils.logging`.
"""

import logging

logger = logging.getLogger(__name__)


def _emit(event, company=None, actor=None, **extra):
    payload = {"event": event}
    if company is not None:
        payload["company_id"] = company.pk
        if getattr(company, "phone_number", None):
            payload["phone"] = company.phone_number
    if actor is not None:
        payload["actor_id"] = getattr(actor, "pk", None)
    payload.update(extra)
    logger.info(event, extra=payload)


def company_registered(company, actor=None):
    _emit("company_registered", company=company, actor=actor)


def step_abandoned(company, step_key, actor=None):
    _emit("company_step_abandoned", company=company, actor=actor, step_key=step_key)


def verification_decided(company, outcome, actor=None):
    _emit("company_verification_decided", company=company, actor=actor, outcome=outcome)


def plan_action_refused(company, missing, actor=None):
    _emit(
        "company_plan_action_refused",
        company=company,
        actor=actor,
        missing=list(missing),
    )


def ownership_transfer_refused(company, actor=None):
    _emit("company_ownership_transfer_refused", company=company, actor=actor)


def companies_archived(user, count):
    logger.info(
        "company_archived_for_user",
        extra={
            "event": "company_archived_for_user",
            "actor_id": getattr(user, "pk", None),
            "count": count,
        },
    )
