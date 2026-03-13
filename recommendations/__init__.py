"""
Staxx Intelligence — Recommendation & ROI Engine

Public surface for the recommendations package.
"""

from recommendations.generator import RecommendationGenerator, SwapCard
from recommendations.roi_engine import ROIEngine, ROIProjection, WaterfallData

__all__ = [
    "RecommendationGenerator",
    "SwapCard",
    "ROIEngine",
    "ROIProjection",
    "WaterfallData",
]
