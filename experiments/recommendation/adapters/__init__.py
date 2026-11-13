"""Domain adapters for offline recommendation experiments."""

from experiments.recommendation.adapters.ecommerce import (
    EcommerceAdapter,
    InteractionEvent,
)

__all__ = ["EcommerceAdapter", "InteractionEvent"]
