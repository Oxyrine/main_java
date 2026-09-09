"""
Configuration parameters for the floor-plan vision pipeline.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class VisionConfig:
    """Knobs and thresholds for 2D floor-plan computer vision extraction."""
    mm_per_px: Optional[float] = None
    known_width_mm: Optional[float] = None
    free_angle: bool = False
    enable_ocr: bool = True
    debug_overlay_path: Optional[str] = None
    working_max_dim: int = 1600
    min_room_area_mm2: float = 1_000_000.0  # 1.0 m^2
    default_wall_height_mm: float = 2800.0
    default_wall_thickness_mm: float = 200.0
    default_door_width_mm: float = 850.0
    default_door_height_mm: float = 2100.0
    default_window_height_mm: float = 1200.0
    default_window_sill_mm: float = 900.0
    default_floor_thickness_mm: float = 50.0
