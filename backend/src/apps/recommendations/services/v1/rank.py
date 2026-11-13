"""Pure ranking of eligible plans against a viewer's nodes."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from apps.recommendations.services.v1.nodes import NodeRepository
from apps.recommendations.services.v1.recommender import Recommender


@dataclass
class PlanRef:
    """One accepted plan for a node."""

    plan_id: int
    distance: float
    published_at: object = None
    features: object = None

    def __getitem__(self, key):
        return getattr(self, key)


@dataclass
class RankedInterest:
    """The accepted plans for one node, ordered by distance."""

    node_id: uuid.UUID
    plans: list[PlanRef] = field(default_factory=list)

    def __getitem__(self, key):
        return getattr(self, key)


class RankService:
    """Computes masked distance and applies the acceptance threshold."""

    def __init__(self, node_repository=None, recommender=None):
        self.nodes = node_repository or NodeRepository()
        self.recommender = recommender or Recommender()

    def rank(
        self, owner_id, space_provider, records, threshold
    ) -> list[RankedInterest]:
        nodes = self.nodes.list_nodes(owner_id)
        if not nodes:
            return []

        bundle = space_provider.load(records)
        ids = list(bundle["ids"])
        values = bundle["values"]
        masks = bundle["masks"]
        published_at = list(bundle["published_at"])
        limit = float(threshold)

        ranked: list[RankedInterest] = []
        for node in nodes:
            distances = self.recommender.distances(values, masks, node.position)
            accepted = [
                index
                for index, distance in enumerate(distances)
                if float(distance) < limit
            ]
            if not accepted:
                ranked.append(RankedInterest(node_id=node.node_id, plans=[]))
                continue
            order = self.recommender.order(
                [ids[index] for index in accepted],
                [float(distances[index]) for index in accepted],
                [published_at[index] for index in accepted],
            )
            distance_of = {ids[index]: float(distances[index]) for index in accepted}
            published_of = {ids[index]: published_at[index] for index in accepted}
            ranked.append(
                RankedInterest(
                    node_id=node.node_id,
                    plans=[
                        PlanRef(
                            plan_id=plan_id,
                            distance=distance_of[plan_id],
                            published_at=published_of[plan_id],
                        )
                        for plan_id in order
                    ],
                )
            )
        return ranked


__all__ = ["PlanRef", "RankedInterest", "RankService"]
