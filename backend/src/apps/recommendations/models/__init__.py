"""Recommendation models."""

from apps.recommendations.models.interest_profile import InterestProfile
from apps.recommendations.models.interest_signal import InterestSignal
from apps.recommendations.models.recommendation_space import RecommendationSpace

__all__ = [
    "InterestProfile",
    "InterestSignal",
    "RecommendationSpace",
]
