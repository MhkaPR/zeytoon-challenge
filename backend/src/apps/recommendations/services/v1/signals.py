"""Record viewer interest signals through the Record service."""

from __future__ import annotations

from django.core.cache import cache
from django.utils import timezone

from apps.recommendations import conf
from apps.recommendations.models import InterestProfile, InterestSignal
from apps.recommendations.services.v1.record import Interaction, RecordService
from apps.recommendations.services.v1.store import PlanSpaceProvider


class SignalRecorder:
    """Applies one signal to the profile that owns the current identity."""

    def __init__(self, provider=None, record_service=None):
        self.provider = provider or PlanSpaceProvider()
        self.record_service = record_service or RecordService()

    def record(
        self,
        records,
        kind,
        plan_ids,
        query="",
        visitor_id=None,
        user=None,
        interaction_id=None,
    ):
        profile, label = self._profile(visitor_id, user)
        if profile is None:
            return {"accepted": 0, "ignored": len(plan_ids), "profile": "none"}

        if not self._within_cap(profile):
            return {"accepted": 0, "ignored": len(plan_ids), "profile": label}

        bundle = self.provider.load(records)
        row_of = {plan_id: index for index, plan_id in enumerate(bundle["ids"])}
        valid = [plan_id for plan_id in plan_ids if plan_id in row_of]
        if not valid:
            return {"accepted": 0, "ignored": len(plan_ids), "profile": label}

        noise = conf.signal_noise(kind)
        owner_id = self._owner_id(profile)
        if kind == InterestSignal.Kind.SEARCH_IMPRESSION:
            rows = [row_of[plan_id] for plan_id in valid]
            centroid = bundle["values"][rows].mean(axis=0)
            mask = bundle["masks"][rows].max(axis=0)
            self.record_service.record(
                owner_id,
                Interaction(
                    vector=centroid.tolist(),
                    weight=noise,
                    kind=kind,
                    mask=mask.tolist(),
                    plan_ids=valid,
                    query=query or "",
                    space_version=bundle["version"],
                    interaction_id=interaction_id,
                ),
                self.provider,
                allow_new_nodes=True,
            )
        else:
            for plan_id in valid:
                row = row_of[plan_id]
                self.record_service.record(
                    owner_id,
                    Interaction(
                        vector=bundle["values"][row].tolist(),
                        weight=noise,
                        kind=kind,
                        mask=bundle["masks"][row].tolist(),
                        plan_ids=[plan_id],
                        query=query or "",
                        space_version=bundle["version"],
                        interaction_id=(
                            f"{interaction_id}:{plan_id}" if interaction_id else None
                        ),
                    ),
                    self.provider,
                    allow_new_nodes=True,
                )
        return {
            "accepted": len(valid),
            "ignored": len(plan_ids) - len(valid),
            "profile": label,
        }

    @staticmethod
    def _owner_id(profile):
        if profile.user_id:
            return profile.user_id
        return profile.visitor_id

    @staticmethod
    def _profile(visitor_id, user):
        if user is not None and getattr(user, "pk", None):
            profile = InterestProfile.objects.filter(user=user).first()
            if profile is None:
                profile = InterestProfile.objects.create(user=user)
            return profile, "user"
        if not visitor_id:
            return None, "none"
        profile = InterestProfile.objects.filter(visitor_id=visitor_id).first()
        if profile is None:
            profile = InterestProfile.objects.create(visitor_id=visitor_id)
        if profile.merged_into_id:
            profile = InterestProfile.objects.filter(
                user_id=profile.merged_into_id
            ).first()
            return profile, "user"
        return profile, "visitor"

    @staticmethod
    def _within_cap(profile):
        identity = (
            f"u{profile.user_id}" if profile.user_id else f"v{profile.visitor_id}"
        )
        minute = timezone.now().strftime("%Y%m%d%H%M")
        key = f"recommendations:cap:{identity}:{minute}"
        cache.add(key, 0, timeout=120)
        try:
            count = cache.incr(key)
        except ValueError:
            cache.set(key, 1, timeout=120)
            count = 1
        return count <= conf.signal_cap_per_minute()
