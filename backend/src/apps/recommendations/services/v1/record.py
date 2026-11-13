"""Absorb one interaction into the nearest node via the Kalman module."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
from django.utils import timezone

from apps.recommendations import conf
from apps.recommendations.models import InterestSignal
from apps.recommendations.services.v1.kalman import KalmanModule
from apps.recommendations.services.v1.nodes import Node, NodeRepository
from apps.recommendations.services.v1.recommender import Recommender


@dataclass
class Interaction:
    """One observed interaction in recommendation-space coordinates."""

    vector: list[float]
    weight: float = 1.0
    kind: str = ""
    occurred_at: datetime | None = None
    interaction_id: str | None = None
    mask: list[float] | None = None
    plan_ids: list[int] = field(default_factory=list)
    query: str = ""
    space_version: str | None = None


class RecordService:
    """Selects the nearest node and delegates state movement to Kalman."""

    def __init__(self, node_repository=None, recommender=None):
        self.nodes = node_repository or NodeRepository()
        self.recommender = recommender or Recommender()

    def record(
        self,
        owner_id,
        interaction,
        space_provider=None,
        allow_new_nodes: bool = False,
    ) -> None:
        profile = self.nodes.resolve_profile(owner_id, create=True)
        if profile is None:
            return
        if self._already_recorded(profile, interaction):
            return

        now = interaction.occurred_at or timezone.now()
        vector = np.asarray(interaction.vector, float)
        mask = self._mask(interaction, vector)
        nodes = self.nodes.list_nodes(owner_id)

        selected, index, distance = self._select(nodes, vector, mask)
        if selected is None or (
            allow_new_nodes and distance > conf.cluster_distance_threshold()
        ):
            selected = Node(
                node_id=uuid.uuid4(),
                position=vector.tolist(),
                uncertainty=[conf.kalman_max_uncertainty()] * len(vector),
                last_updated_at=now,
                signal_count=0,
                activity=0.0,
            )
            nodes.append(selected)
            index = len(nodes) - 1

        position, uncertainty, _ = KalmanModule.apply(
            selected.position,
            selected.uncertainty,
            vector,
            last_updated_at=selected.last_updated_at,
            now=now,
            mask=mask,
            weight=interaction.weight,
            process_noise=conf.kalman_process_noise(),
            measurement_noise=conf.kalman_measurement_noise(),
        )
        selected.position = position.tolist()
        selected.uncertainty = uncertainty.tolist()
        selected.signal_count += 1
        selected.last_updated_at = now

        self._decay_activity(nodes, index)
        nodes = self._enforce_cap(nodes)

        profile.signal_count += 1
        profile.last_signal_at = now
        self.nodes.save_nodes(
            profile,
            nodes,
            space_version=interaction.space_version or profile.space_version or "",
            signal_count=profile.signal_count,
        )
        self._write_signal(profile, interaction)

    @staticmethod
    def _already_recorded(profile, interaction) -> bool:
        if not interaction.interaction_id:
            return False
        return InterestSignal.objects.filter(
            profile=profile, interaction_id=interaction.interaction_id
        ).exists()

    @staticmethod
    def _mask(interaction, vector):
        if interaction.mask is None:
            return np.ones_like(vector, dtype=bool)
        return np.asarray(interaction.mask, bool)

    def _select(self, nodes, vector, mask):
        if not nodes:
            return None, None, float("inf")
        distances = [
            float(
                self.recommender.distances(
                    np.asarray([vector]), np.asarray([mask]), node.position
                )[0]
            )
            for node in nodes
        ]
        index = int(np.argmin(distances))
        return nodes[index], index, distances[index]

    @staticmethod
    def _decay_activity(nodes, selected_index):
        decay = conf.cluster_activity_decay()
        for index, node in enumerate(nodes):
            node.activity *= decay
            if index == selected_index:
                node.activity += 1.0

    @staticmethod
    def _enforce_cap(nodes):
        limit = max(int(conf.max_interest_clusters()), 1)
        if len(nodes) <= limit:
            return nodes
        worst = min(
            range(len(nodes)),
            key=lambda index: (
                nodes[index].activity,
                -float(np.mean(nodes[index].uncertainty)),
            ),
        )
        nodes.pop(worst)
        return nodes

    @staticmethod
    def _write_signal(profile, interaction):
        InterestSignal.objects.create(
            profile=profile,
            kind=interaction.kind,
            plan_ids=list(interaction.plan_ids or []),
            query=interaction.query or "",
            weight=float(interaction.weight),
            interaction_id=interaction.interaction_id,
        )


__all__ = ["Interaction", "RecordService"]
