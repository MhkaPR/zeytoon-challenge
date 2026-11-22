"""Node storage backed by the existing ``InterestProfile`` clusters.

Each cluster in ``InterestProfile.position`` is a node. Per-node metadata
(stable id, last update time, signal count) lives in parallel JSON fields on the
same row, so no new persisted model is required.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from apps.recommendations.models import InterestProfile

_NODE_NAMESPACE = uuid.UUID("6f1d3c2a-8b4e-4f7a-9c1d-2e3f4a5b6c7d")


@dataclass
class Node:
    """One distinct interest owned by a viewer."""

    node_id: uuid.UUID
    position: list[float]
    uncertainty: list[float]
    last_updated_at: datetime
    signal_count: int = 0
    activity: float = 1.0
    extra: dict = field(default_factory=dict)


def _as_vectors(value):
    """Normalize a flat vector or a list of vectors into a list of vectors."""
    if not value:
        return []
    first = value[0]
    if isinstance(first, (int, float)):
        return [list(value)]
    return [list(row) for row in value]


def _parse_moment(raw):
    if not raw:
        return None
    if isinstance(raw, datetime):
        moment = raw
    else:
        try:
            moment = datetime.fromisoformat(str(raw))
        except ValueError:
            return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment


class NodeRepository:
    """Read and write nodes for one owner (visitor UUID or user pk)."""

    @staticmethod
    def is_visitor(owner_id) -> bool:
        if hasattr(owner_id, "pk"):
            return False
        return isinstance(owner_id, uuid.UUID) or (
            isinstance(owner_id, str) and _looks_like_uuid(owner_id)
        )

    def resolve_profile(self, owner_id, create=False):
        if owner_id is None:
            return None
        if hasattr(owner_id, "pk"):
            owner_id = owner_id.pk
        if self.is_visitor(owner_id):
            visitor = uuid.UUID(str(owner_id))
            profile = InterestProfile.objects.filter(visitor_id=visitor).first()
            if profile is None:
                if not create:
                    return None
                return InterestProfile.objects.create(visitor_id=visitor)
            if profile.merged_into_id:
                account = InterestProfile.objects.filter(
                    user_id=profile.merged_into_id
                ).first()
                if account is not None:
                    return account
            return profile

        profile = InterestProfile.objects.filter(user_id=owner_id).first()
        if profile is None and create:
            return InterestProfile.objects.create(user_id=owner_id)
        return profile

    def list_nodes(self, owner_id) -> list[Node]:
        profile = self.resolve_profile(owner_id)
        if profile is None:
            return []
        positions = _as_vectors(profile.position)
        uncertainties = _as_vectors(profile.uncertainty)
        activities = list(profile.activity_profile or [])
        node_ids = list(profile.node_ids or [])
        updated = list(profile.node_updated_at or [])
        counts = list(profile.node_signal_counts or [])
        fallback_moment = profile.last_signal_at or profile.updated_at
        nodes: list[Node] = []
        for index, position in enumerate(positions):
            uncertainty = (
                uncertainties[index]
                if index < len(uncertainties)
                else [1.0] * len(position)
            )
            raw_id = node_ids[index] if index < len(node_ids) else None
            node_id = _coerce_uuid(raw_id) or uuid.uuid5(
                _NODE_NAMESPACE, f"{profile.pk}:{index}"
            )
            moment = (
                (_parse_moment(updated[index]) if index < len(updated) else None)
                or fallback_moment
                or profile.updated_at
            )
            nodes.append(
                Node(
                    node_id=node_id,
                    position=list(position),
                    uncertainty=list(uncertainty),
                    last_updated_at=moment,
                    signal_count=(
                        int(counts[index])
                        if index < len(counts)
                        else (profile.signal_count if index == 0 else 0)
                    ),
                    activity=(
                        float(activities[index]) if index < len(activities) else 1.0
                    ),
                )
            )
        return nodes

    def save_nodes(self, profile, nodes, space_version=None, signal_count=None):
        """Persist every node for ``profile`` in one write."""
        profile.position = [list(node.position) for node in nodes]
        profile.uncertainty = [list(node.uncertainty) for node in nodes]
        profile.activity_profile = [float(node.activity) for node in nodes]
        profile.node_ids = [str(node.node_id) for node in nodes]
        profile.node_updated_at = [node.last_updated_at.isoformat() for node in nodes]
        profile.node_signal_counts = [int(node.signal_count) for node in nodes]
        if space_version is not None:
            profile.space_version = space_version
        if signal_count is not None:
            profile.signal_count = signal_count
        profile.save(
            update_fields=(
                "position",
                "uncertainty",
                "activity_profile",
                "node_ids",
                "node_updated_at",
                "node_signal_counts",
                "space_version",
                "signal_count",
                "updated_at",
            )
        )


def _looks_like_uuid(value) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def _coerce_uuid(value):
    if value is None:
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


__all__ = ["Node", "NodeRepository"]
