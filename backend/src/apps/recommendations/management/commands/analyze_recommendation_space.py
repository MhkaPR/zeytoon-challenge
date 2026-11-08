"""Inspect recommendation vectors, interest clusters, and ranking for one viewer."""

from __future__ import annotations

import json

import numpy as np
from django.core.management.base import BaseCommand, CommandError

from apps.catalog.models import PublishedRecord
from apps.pipeline.interfaces import PipelineInterface
from apps.recommendations import conf
from apps.recommendations.models import InterestProfile
from apps.recommendations.services.v1.features import PlanFeatureMapper
from apps.recommendations.services.v1.recommender import Recommender
from apps.recommendations.services.v1.space import PlanSpace
from apps.recommendations.services.v1.state import InterestClusters


class Command(BaseCommand):
    help = (
        "Print the fitted recommendation space, per-plan vectors, a viewer's "
        "interest clusters, and the resulting related-plan order."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--query",
            default="",
            help="Only show plans whose company name or values contain this text.",
        )
        parser.add_argument(
            "--plan-id",
            action="append",
            type=int,
            default=[],
            help="Show the full vector for this plan id (repeatable).",
        )
        parser.add_argument("--visitor-id", default=None)
        parser.add_argument("--user-id", type=int, default=None)
        parser.add_argument("--profile-id", type=int, default=None)
        parser.add_argument("--top", type=int, default=20)
        parser.add_argument(
            "--show-vectors",
            action="store_true",
            help="Print named values for every plan in the selected result.",
        )
        parser.add_argument(
            "--show-masks",
            action="store_true",
            help="Print the existence mask alongside each vector.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            dest="as_json",
            help="Emit machine-readable JSON instead of text.",
        )

    def handle(self, *args, **options):
        bundle = self._build_bundle()
        profile = self._profile(options)
        clusters = InterestClusters.from_profile(profile, bundle)
        records = self._records()
        by_id = {record["id"]: record for record in records}
        row_of = {plan_id: index for index, plan_id in enumerate(bundle["ids"])}

        selected_ids = self._selected_ids(
            records, options["query"], options["plan_id"]
        )
        ranking = self._ranking(bundle, clusters, options["top"])

        if options["as_json"]:
            self.stdout.write(
                json.dumps(
                    self._payload(
                        bundle,
                        profile,
                        clusters,
                        records,
                        selected_ids,
                        ranking,
                    ),
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return

        self._print_space(bundle, profile, clusters)
        if selected_ids:
            self._print_vectors(
                bundle,
                clusters,
                by_id,
                row_of,
                selected_ids,
                options,
            )
        self._print_clusters(bundle, clusters, by_id)
        self._print_ranking(bundle, clusters, by_id, row_of, ranking)

    def _records(self):
        rows = PublishedRecord.objects.filter(is_published=True).order_by(
            "-published_at", "id"
        )
        return list(
            rows.values("id", "site", "plan_type", "values", "published_at")
        )

    def _build_bundle(self):
        records = [
            {
                "id": record["id"],
                "values": record["values"],
                "published_at": record["published_at"],
            }
            for record in self._records()
        ]
        if not records:
            raise CommandError("no published plans to analyse")
        features = [PlanFeatureMapper().map(record) for record in records]
        space = PlanSpace(n_bins=conf.n_bins()).fit(features)
        values, masks = space.transform(features)
        return {
            "version": space.version(features),
            "space": space,
            "values": values,
            "masks": masks,
            "ids": [feature["id"] for feature in features],
            "published_at": [feature["published_at"] for feature in features],
        }

    @staticmethod
    def _profile(options):
        if options["profile_id"]:
            profile = InterestProfile.objects.filter(pk=options["profile_id"]).first()
            if profile is None:
                raise CommandError(f"profile {options['profile_id']} not found")
            return profile
        if options["visitor_id"]:
            profile = InterestProfile.objects.filter(
                visitor_id=options["visitor_id"]
            ).first()
            if profile is None:
                raise CommandError(f"visitor {options['visitor_id']} not found")
            return profile
        if options["user_id"]:
            profile = InterestProfile.objects.filter(user_id=options["user_id"]).first()
            if profile is None:
                raise CommandError(f"user {options['user_id']} not found")
            return profile
        return None

    @staticmethod
    def _selected_ids(records, query, plan_ids):
        selected = set(plan_ids)
        needle = query.strip().casefold()
        if not needle:
            return selected
        sites = PipelineInterface.public_site_details(
            [record["site"] for record in records]
        )
        for record in records:
            site = sites.get(record["site"])
            if site is None:
                continue
            haystack = f"{site['company_name']} {record['values']}".casefold()
            if needle in haystack:
                selected.add(record["id"])
        return selected

    @staticmethod
    def _ranking(bundle, clusters, top):
        nearest, distances = clusters.nearest_clusters(
            bundle["values"], bundle["masks"]
        )
        ranks = clusters.cluster_ranks(nearest, distances)
        ordered = Recommender.order_by_cluster(
            bundle["ids"], distances, bundle["published_at"], ranks
        )
        distance_of = {
            plan_id: float(distances[index])
            for index, plan_id in enumerate(bundle["ids"])
        }
        published_of = {
            plan_id: bundle["published_at"][index]
            for index, plan_id in enumerate(bundle["ids"])
        }
        return [
            (plan_id, distance_of[plan_id], published_of[plan_id])
            for plan_id in ordered[: max(int(top), 0)]
        ]

    def _print_space(self, bundle, profile, clusters):
        space = bundle["space"]
        semantic = [name for name in space.names if name.startswith("semantic_")]
        self._line("Space")
        self._kv("version", bundle["version"])
        self._kv("plans", len(bundle["ids"]))
        self._kv("dimensions", len(space.names))
        self._kv("semantic_dimensions", len(semantic))
        self._kv("fitted_semantic_dimensions", space.semantic.fitted_components)
        self._kv(
            "profile",
            "cold start"
            if profile is None
            else f"#{profile.pk} visitor={profile.visitor_id} user={profile.user_id}",
        )
        self._kv("cluster_count", len(clusters.states))
        self._line("")

    def _print_vectors(self, bundle, clusters, by_id, row_of, selected_ids, options):
        self._line("Vectors")
        for plan_id in sorted(selected_ids):
            index = row_of.get(plan_id)
            record = by_id.get(plan_id)
            if index is None or record is None:
                continue
            distance = float(
                clusters.distances(
                    bundle["values"][[index]], bundle["masks"][[index]]
                )[0]
            )
            self._line(
                f"  #{plan_id} {record['plan_type']} "
                f"{record['values'].get('plan_name')!r} distance={distance:.4f}"
            )
            if options["show_vectors"]:
                self._named_vector(
                    "    values", bundle["space"].names, bundle["values"][index]
                )
            if options["show_masks"]:
                self._named_vector(
                    "    masks", bundle["space"].names, bundle["masks"][index]
                )
        self._line("")

    def _print_clusters(self, bundle, clusters, by_id):
        self._line("Clusters")
        if not clusters.states:
            self._line("  (cold start: one prior cluster)")
            self._line("")
            return
        for cluster_index, state in enumerate(clusters.states):
            per_plan = np.sqrt(
                (((bundle["values"] - state.x) ** 2) * bundle["masks"]).sum(axis=1)
                / np.maximum(bundle["masks"].sum(axis=1), 1)
            )
            nearest = np.argsort(per_plan)[:5]
            self._line(
                f"  cluster {cluster_index}: mean_uncertainty="
                f"{float(np.mean(state.s)):.3f} "
                f"last_active={clusters.activity[cluster_index]}"
            )
            for index in nearest:
                plan_id = bundle["ids"][index]
                record = by_id.get(plan_id, {})
                self._line(
                    f"    {float(per_plan[index]):.4f} #{plan_id} "
                    f"{record.get('plan_type', '?')} "
                    f"{record.get('values', {}).get('plan_name')!r}"
                )
        self._line("")

    def _print_ranking(self, bundle, clusters, by_id, row_of, ranking):
        self._line("Related order")
        for rank, (plan_id, distance, _published_at) in enumerate(ranking, start=1):
            record = by_id.get(plan_id, {})
            index = row_of[plan_id]
            per_cluster = [
                float(
                    np.sqrt(
                        (
                            ((bundle["values"][index] - state.x) ** 2)
                            * bundle["masks"][index]
                        ).sum()
                        / max(bundle["masks"][index].sum(), 1)
                    )
                )
                for state in clusters.states
            ]
            self._line(
                f"  {rank:>3}. {distance:.4f} #{plan_id} "
                f"{record.get('plan_type', '?')} "
                f"{record.get('values', {}).get('plan_name')!r} "
                f"per_cluster={[round(value, 4) for value in per_cluster]}"
            )

    @staticmethod
    def _payload(
        bundle,
        profile,
        clusters,
        records,
        selected_ids,
        ranking,
    ):
        row_of = {plan_id: index for index, plan_id in enumerate(bundle["ids"])}
        by_id = {record["id"]: record for record in records}
        vectors = []
        for plan_id in sorted(selected_ids):
            index = row_of.get(plan_id)
            if index is None:
                continue
            vectors.append(
                {
                    "id": plan_id,
                    "values": bundle["values"][index].tolist(),
                    "masks": bundle["masks"][index].tolist(),
                }
            )
        return {
            "space": {
                "version": bundle["version"],
                "plans": len(bundle["ids"]),
                "names": bundle["space"].names,
                "semantic_dimensions": bundle["space"].semantic.dimensions,
                "fitted_semantic_dimensions": bundle["space"].semantic.fitted_components,
            },
            "profile": (
                None
                if profile is None
                else {
                    "id": profile.pk,
                    "visitor_id": str(profile.visitor_id) if profile.visitor_id else None,
                    "user_id": profile.user_id,
                    "signal_count": profile.signal_count,
                    "clusters": clusters.positions,
                    "uncertainties": clusters.uncertainties,
                    "activity": clusters.activity,
                }
            ),
            "vectors": vectors,
            "ranking": [
                {
                    "rank": rank,
                    "id": plan_id,
                    "distance": distance,
                    "plan_type": by_id.get(plan_id, {}).get("plan_type"),
                    "plan_name": by_id.get(plan_id, {})
                    .get("values", {})
                    .get("plan_name"),
                }
                for rank, (plan_id, distance, _published_at) in enumerate(
                    ranking, start=1
                )
            ],
        }

    def _named_vector(self, label, names, vector):
        pairs = [
            f"{name}={float(value):.3f}"
            for name, value in zip(names, vector)
            if abs(float(value)) > 1e-9
        ]
        self._line(f"{label}: " + ", ".join(pairs))

    def _kv(self, key, value):
        self._line(f"  {key}: {value}")

    def _line(self, text):
        self.stdout.write(text)
