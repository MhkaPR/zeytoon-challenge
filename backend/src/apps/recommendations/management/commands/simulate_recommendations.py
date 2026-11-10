"""Replay configurable synthetic signals and inspect the resulting suggestions."""

from __future__ import annotations

import json
import uuid

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from apps.accounts.validation import normalize_phone
from apps.catalog.filters import normalize_resource_value
from apps.catalog.models import PublishedRecord
from apps.recommendations.models import InterestProfile, InterestSignal
from apps.recommendations.services.v1.ranking import RankingService
from apps.recommendations.services.v1.signals import SignalRecorder
from apps.recommendations.services.v1.state import InterestClusters
from apps.recommendations.services.v1.store import PlanSpaceProvider


class Command(BaseCommand):
    help = (
        "Replay configurable synthetic clicks/searches for one visitor and print "
        "the stored profile, active clusters, selected plans, and explanations."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--visitor-id",
            default=None,
            help="Visitor UUID to simulate. Defaults to a fresh UUID.",
        )
        parser.add_argument(
            "--user-id",
            type=int,
            default=None,
            help="Simulate signals for an authenticated user id.",
        )
        parser.add_argument(
            "--phone-number",
            default=None,
            help="Simulate signals for the user with this phone number.",
        )
        parser.add_argument(
            "--kind",
            choices=[kind.value for kind in InterestSignal.Kind],
            default=None,
            help=(
                "Signal kind to record. Defaults to search_impression when "
                "--query is set, otherwise destination_visit."
            ),
        )
        parser.add_argument(
            "--count",
            type=int,
            default=10,
            help="Number of signals to record.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Plans per signal (search impressions usually use 12).",
        )
        parser.add_argument("--query", default="", help="Query for search impressions.")
        parser.add_argument("--plan-type", default=None, help="Filter by plan_type.")
        parser.add_argument("--min-price", type=float, default=None)
        parser.add_argument("--max-price", type=float, default=None)
        parser.add_argument("--min-ram", type=float, default=None)
        parser.add_argument("--min-cpu", type=float, default=None)
        parser.add_argument("--min-disk", type=float, default=None)
        parser.add_argument(
            "--top",
            type=int,
            default=20,
            help="Number of suggested plans to request.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete the visitor profile before simulating.",
        )
        parser.add_argument(
            "--keep",
            action="store_true",
            help="Keep the simulated visitor profile after the run.",
        )
        parser.add_argument(
            "--cleanup",
            action="store_true",
            help="Hard-delete the simulated user profile after the run.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            dest="as_json",
            help="Emit machine-readable JSON.",
        )

    def handle(self, *args, **options):
        kind = options["kind"] or (
            InterestSignal.Kind.SEARCH_IMPRESSION.value
            if options["query"]
            else InterestSignal.Kind.DESTINATION_VISIT.value
        )
        limit = options["limit"]
        if limit is None:
            limit = (
                12
                if kind == InterestSignal.Kind.SEARCH_IMPRESSION.value
                else 1
            )
        options["kind"] = kind
        options["limit"] = limit

        user = self._user(options)
        visitor = None
        if user is None:
            visitor = (
                uuid.UUID(options["visitor_id"])
                if options["visitor_id"]
                else uuid.uuid4()
            )
        if options["reset"]:
            for existing in self._profiles(user, visitor):
                existing.hard_delete()

        records = list(
            PublishedRecord.objects.filter(is_published=True).values(
                "id", "values", "published_at", "plan_type"
            )
        )
        if not records:
            raise CommandError("no published plans available")
        selected = self._filter_records(records, options)
        if not selected:
            raise CommandError("no published plans matched the filters")

        recorder = SignalRecorder()
        for index in range(max(int(options["count"]), 0)):
            plan_ids = self._plan_ids_for_signal(selected, index, options)
            result = recorder.record(
                records,
                options["kind"],
                plan_ids,
                query=options["query"],
                visitor_id=visitor,
                user=user,
            )
            if result["accepted"] == 0:
                raise CommandError(
                    "the signal recorder rejected the synthetic signal; "
                    "check the signal cap or plan ids"
                )

        profile = self._profiles(user, visitor).first()
        if profile is None:
            raise CommandError("simulation did not create a profile")

        bundle = PlanSpaceProvider().load(records)
        clusters = InterestClusters.from_profile(profile, bundle)
        suggestions = RankingService().suggest_with_explanations(
            records,
            visitor_id=visitor,
            user=user,
            limit=options["top"],
        )
        payload = self._payload(
            user,
            visitor,
            profile,
            bundle,
            clusters,
            selected,
            suggestions,
            records,
            options["kind"],
            options["query"],
        )
        if options["as_json"]:
            self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            self._print_text(payload)

        if options["cleanup"] or (user is None and not options["keep"]):
            profile.hard_delete()

    @staticmethod
    def _user(options):
        User = get_user_model()
        if options["user_id"]:
            user = User.objects.filter(pk=options["user_id"]).first()
            if user is None:
                raise CommandError(f"user {options['user_id']} not found")
            return user
        if options["phone_number"]:
            raw = options["phone_number"].strip()
            normalized = normalize_phone(raw) or raw
            user = User.objects.filter(
                Q(phone_number=raw) | Q(phone_number=normalized)
            ).first()
            if user is None:
                raise CommandError(f"user with phone {raw} not found")
            return user
        return None

    @staticmethod
    def _profiles(user, visitor):
        if user is not None:
            return InterestProfile.objects.filter(user=user)
        return InterestProfile.objects.filter(visitor_id=visitor)

    @staticmethod
    def _filter_records(records, options):
        selected = []
        query = (options["query"] or "").casefold()
        for record in records:
            values = record.get("values") or {}
            if query and query not in str(values).casefold():
                continue
            if options["plan_type"] and record.get("plan_type") != options["plan_type"]:
                continue
            price = _number(values.get("price_amount", values.get("price")))
            if options["min_price"] is not None and (
                price is None or price < options["min_price"]
            ):
                continue
            if options["max_price"] is not None and (
                price is None or price > options["max_price"]
            ):
                continue
            if not _meets_resource(values, "ram", options["min_ram"]):
                continue
            if not _meets_resource(values, "cpu", options["min_cpu"]):
                continue
            if not _meets_resource(values, "disk", options["min_disk"]):
                continue
            selected.append(record)
        return selected

    @staticmethod
    def _plan_ids_for_signal(records, index, options):
        limit = max(int(options["limit"]), 1)
        start = (index * limit) % len(records)
        return [
            records[(start + offset) % len(records)]["id"]
            for offset in range(min(limit, len(records)))
        ]

    @staticmethod
    def _payload(
        user,
        visitor,
        profile,
        bundle,
        clusters,
        selected,
        suggestions,
        records,
        kind,
        query,
    ):
        by_id = {record["id"]: record for record in records}
        active_ids = {id(state) for state in clusters.active_states()}
        return {
            "identity": f"user:{user.pk}" if user is not None else f"visitor:{visitor}",
            "visitor_id": str(visitor) if visitor is not None else None,
            "user_id": user.pk if user is not None else None,
            "kind": kind,
            "query": query,
            "profile": {
                "signal_count": profile.signal_count,
                "positions": profile.position,
                "uncertainties": profile.uncertainty,
                "activities": profile.activity_profile,
            },
            "clusters": [
                {
                    "index": index,
                    "activity": float(state.activity),
                    "active": id(state) in active_ids,
                    "position": state.x.tolist(),
                    "uncertainty": state.s.tolist(),
                }
                for index, state in enumerate(clusters.states)
            ],
            "simulated_plans": [
                _plan_summary(record) for record in selected[:20]
            ],
            "suggested_plan_ids": suggestions["plan_ids"],
            "suggested_plans": [
                _plan_summary(by_id[plan_id])
                for plan_id in suggestions["plan_ids"]
                if plan_id in by_id
            ],
            "explanations": suggestions["explanations"],
        }

    def _print_text(self, payload):
        self.stdout.write(f"identity: {payload['identity']}")
        self.stdout.write(
            f"signal: kind={payload['kind']} query={payload['query']!r}"
        )
        profile = payload["profile"]
        self.stdout.write(
            f"profile: signals={profile['signal_count']} "
            f"activities={profile['activities']}"
        )
        self.stdout.write("clusters:")
        for cluster in payload["clusters"]:
            self.stdout.write(
                f"  {cluster['index']}: activity={cluster['activity']:.6f} "
                f"active={cluster['active']}"
            )
        self.stdout.write("simulated plans:")
        for plan in payload["simulated_plans"]:
            self.stdout.write(
                f"  #{plan['id']} {plan['plan_type']} {plan['name']!r} "
                f"price={plan['price']} ram={plan['ram']} "
                f"cpu={plan['cpu']} disk={plan['disk']}"
            )
        self.stdout.write("explanations:")
        for explanation in payload["explanations"]:
            self.stdout.write(
                f"  cluster={explanation['cluster_id']} "
                f"intent={explanation['intent']} "
                f"message={explanation['message']!r} "
                f"plans={explanation['plan_ids']}"
            )
        self.stdout.write("suggested plans:")
        for plan in payload["suggested_plans"]:
            self.stdout.write(
                f"  #{plan['id']} {plan['plan_type']} {plan['name']!r} "
                f"price={plan['price']} ram={plan['ram']} "
                f"cpu={plan['cpu']} disk={plan['disk']}"
            )


def _number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _meets_resource(values, resource, minimum):
    if minimum is None:
        return True
    value = normalize_resource_value(resource, values)
    return value is not None and value >= minimum


def _plan_summary(record):
    values = record.get("values") or {}
    return {
        "id": record.get("id"),
        "plan_type": record.get("plan_type"),
        "name": values.get("plan_name") or values.get("title") or values.get("name"),
        "price": _number(values.get("price_amount", values.get("price"))),
        "ram": normalize_resource_value("ram", values),
        "cpu": normalize_resource_value("cpu", values),
        "disk": normalize_resource_value("disk", values),
    }


__all__ = ["Command"]
