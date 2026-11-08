"""Record viewer interest signals into a preference profile."""

from __future__ import annotations

from django.core.cache import cache
from django.utils import timezone

from apps.recommendations import conf
from apps.recommendations.models import InterestProfile, InterestSignal
from apps.recommendations.services.v1.state import InterestClusters
from apps.recommendations.services.v1.store import PlanSpaceProvider


class SignalRecorder:
    """Applies one signal to the profile that owns the current identity."""

    def __init__(self, provider=None):
        self.provider = provider or PlanSpaceProvider()

    def record(self, records, kind, plan_ids, query="", visitor_id=None, user=None):
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

        state = self._state(profile, bundle)
        noise = conf.signal_noise(kind)
        if kind == InterestSignal.Kind.SEARCH_IMPRESSION:
            rows = [row_of[plan_id] for plan_id in valid]
            centroid = bundle["values"][rows].mean(axis=0)
            mask = bundle["masks"][rows].max(axis=0)
            state.update(centroid, mask, noise)
        else:
            for plan_id in valid:
                row = row_of[plan_id]
                state.update(bundle["values"][row], bundle["masks"][row], noise)

        self._save(profile, state, bundle["version"])
        InterestSignal.objects.create(
            profile=profile,
            kind=kind,
            plan_ids=valid,
            query=query or "",
            weight=noise,
        )
        return {
            "accepted": len(valid),
            "ignored": len(plan_ids) - len(valid),
            "profile": label,
        }

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
            profile = InterestProfile.objects.filter(user_id=profile.merged_into_id).first()
            return profile, "user"
        return profile, "visitor"

    @staticmethod
    def _within_cap(profile):
        identity = f"u{profile.user_id}" if profile.user_id else f"v{profile.visitor_id}"
        minute = timezone.now().strftime("%Y%m%d%H%M")
        key = f"recommendations:cap:{identity}:{minute}"
        cache.add(key, 0, timeout=120)
        try:
            count = cache.incr(key)
        except ValueError:
            cache.set(key, 1, timeout=120)
            count = 1
        return count <= conf.signal_cap_per_minute()

    @staticmethod
    def _state(profile, bundle):
        return InterestClusters.from_profile(profile, bundle, cold_start=False)

    @staticmethod
    def _save(profile, state, version):
        profile.position = state.positions
        profile.uncertainty = state.uncertainties
        profile.cluster_activity = state.activity
        profile.space_version = version
        profile.signal_count += 1
        profile.last_signal_at = timezone.now()
        profile.save(
            update_fields=(
                "position",
                "uncertainty",
                "cluster_activity",
                "space_version",
                "signal_count",
                "last_signal_at",
                "updated_at",
            )
        )
