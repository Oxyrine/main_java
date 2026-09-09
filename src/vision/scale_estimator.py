"""
Scale estimation stage: chained fallback inference using door swing arcs,
known building dimensions, or legacy fallback.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import numpy as np

from src.vision.config import VisionConfig
from src.vision.opening_detector import Opening


@dataclass
class ScaleEstimate:
    """Estimated scale factor and confidence metrics."""
    mm_per_px: float
    method: str
    confidence: float


class ScaleEstimator:
    """Calculates millimeter-to-pixel scale factor using chained heuristic policy."""

    def estimate(
        self,
        openings: List[Opening],
        building_width_px: float,
        config: VisionConfig
    ) -> ScaleEstimate:
        """
        Estimates mm_per_px using chained fallback:
        1. Explicit config.mm_per_px override
        2. Explicit config.known_width_mm
        3. Median door swing arc (~850 mm)
        4. Legacy default 12,000 mm building width
        """
        # 1. Explicit override
        if config.mm_per_px is not None and config.mm_per_px > 0:
            return ScaleEstimate(
                mm_per_px=float(config.mm_per_px),
                method="manual_override",
                confidence=1.0,
            )

        # 2. Known building width
        if config.known_width_mm is not None and config.known_width_mm > 0:
            bw = max(50.0, building_width_px)
            return ScaleEstimate(
                mm_per_px=float(config.known_width_mm / bw),
                method="known_width",
                confidence=0.95,
            )

        # 3. Door arc inference (median door is ~850mm worldwide)
        door_radii = [op.arc_radius_px for op in openings if op.kind == "door" and op.arc_radius_px is not None]
        if door_radii:
            median_radius = float(np.median(door_radii))
            if median_radius > 10.0:
                est_mm_per_px = config.default_door_width_mm / median_radius
                return ScaleEstimate(
                    mm_per_px=est_mm_per_px,
                    method="door_arc_inference",
                    confidence=0.85,
                )

        # 4. Fallback legacy assumption (12m envelope)
        bw = max(100.0, building_width_px)
        fallback_mm_per_px = 12000.0 / bw
        return ScaleEstimate(
            mm_per_px=fallback_mm_per_px,
            method="legacy_width_fallback",
            confidence=0.40,
        )
