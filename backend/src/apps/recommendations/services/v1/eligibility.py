"""Candidate eligibility based on declared plan resources."""

from __future__ import annotations

import numpy as np

from apps.recommendations import conf

RESOURCE_FIELDS = ("cpu", "ram", "disk", "traffic")


def eligible_rows(bundle) -> np.ndarray:
    """Return a mask of plans that declare enough comparable resources.

    Plans with only a price (licenses, domains, add-ons) would otherwise rank
    against any interest because missing dimensions are masked out of the
    distance. Requiring at least one declared resource keeps those catalogue
    entries out of the suggested-plans surface.
    """
    names = list(bundle["space"].names)
    indices = [
        names.index(f"has_{field}")
        for field in RESOURCE_FIELDS
        if f"has_{field}" in names
    ]
    total = bundle["values"].shape[0]
    if not indices:
        return np.ones(total, dtype=bool)
    declared = (bundle["values"][:, indices] > 0) & (
        bundle["masks"][:, indices] > 0
    )
    minimum = max(int(conf.min_resource_dimensions()), 0)
    return declared.sum(axis=1) >= minimum


__all__ = ["eligible_rows"]
