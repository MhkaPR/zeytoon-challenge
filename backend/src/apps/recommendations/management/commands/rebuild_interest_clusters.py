"""Rebuild multi-interest clusters from each profile's recorded signals."""

from django.core.management.base import BaseCommand

from apps.catalog.interfaces import CatalogInterface
from apps.recommendations import conf
from apps.recommendations.models import InterestProfile, InterestSignal
from apps.recommendations.services.v1.state import InterestClusters
from apps.recommendations.services.v1.store import PlanSpaceProvider


class Command(BaseCommand):
    help = "Replay recorded signals into interest clusters."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--visitor-id", default=None)
        parser.add_argument("--user-id", type=int, default=None)

    def handle(self, *args, **options):
        records = CatalogInterface.published_plan_records()
        bundle = PlanSpaceProvider().load(records)
        row_of = {plan_id: index for index, plan_id in enumerate(bundle["ids"])}
        profiles = InterestProfile.objects.all()
        if options["visitor_id"]:
            profiles = profiles.filter(visitor_id=options["visitor_id"])
        if options["user_id"]:
            profiles = profiles.filter(user_id=options["user_id"])

        for profile in profiles:
            clusters = InterestClusters([])
            for signal in profile.signals.order_by("created_at"):
                rows = [
                    row_of[plan_id]
                    for plan_id in (signal.plan_ids or [])
                    if plan_id in row_of
                ]
                if not rows:
                    continue
                noise = signal.weight or conf.signal_noise(signal.kind)
                if signal.kind == InterestSignal.Kind.SEARCH_IMPRESSION:
                    clusters.update(
                        bundle["values"][rows].mean(axis=0),
                        bundle["masks"][rows].max(axis=0),
                        noise,
                    )
                    continue
                for row in rows:
                    clusters.update(
                        bundle["values"][row],
                        bundle["masks"][row],
                        noise,
                    )

            if not options["dry_run"]:
                profile.position = clusters.positions
                profile.uncertainty = clusters.uncertainties
                profile.activity_profile = clusters.activities
                profile.space_version = bundle["version"]
                profile.save(
                    update_fields=(
                        "position",
                        "uncertainty",
                        "activity_profile",
                        "space_version",
                        "updated_at",
                    )
                )
            self.stdout.write(
                f"profile {profile.pk}: {len(clusters.states)} cluster(s)"
                + (" (dry run)" if options["dry_run"] else "")
            )
