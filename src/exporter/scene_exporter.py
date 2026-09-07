"""Serializes BlueprintElement domain models into structured 3D scene data for Lane 3."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from src.models import BlueprintElement, Vector3D


class SceneExporter:
    """
    Transforms a collection of BlueprintElements into a clean 3D scene graph representation.
    Handles coordinate normalization, unit conversions, composite bounding-box calculation,
    and schema-compliant JSON generation.
    """

    UNIT_CONVERSIONS = {
        ("mm", "m"): 0.001,
        ("cm", "m"): 0.01,
        ("m", "m"): 1.0,
        ("inch", "m"): 0.0254,
        ("foot", "m"): 0.3048,
    }

    def __init__(self, source_units: str = "mm", target_units: str = "m") -> None:
        self.source_units = source_units.lower()
        self.target_units = target_units.lower()
        self.unit_scale: float = self.UNIT_CONVERSIONS.get(
            (self.source_units, self.target_units), 1.0
        )

    def calculate_scene_bounds(self, elements: List[BlueprintElement]) -> Dict[str, List[float]]:
        """Compute the composite axis-aligned bounding box across all elements in target units."""
        if not elements:
            return {"min": [0.0, 0.0, 0.0], "max": [0.0, 0.0, 0.0]}

        all_mins: List[Vector3D] = []
        all_maxs: List[Vector3D] = []

        for elem in elements:
            b_min, b_max = elem.get_bounding_box()
            all_mins.append(b_min)
            all_maxs.append(b_max)

        min_x = min(v.x for v in all_mins) * self.unit_scale
        min_y = min(v.y for v in all_mins) * self.unit_scale
        min_z = min(v.z for v in all_mins) * self.unit_scale

        max_x = max(v.x for v in all_maxs) * self.unit_scale
        max_y = max(v.y for v in all_maxs) * self.unit_scale
        max_z = max(v.z for v in all_maxs) * self.unit_scale

        return {
            "min": [round(min_x, 3), round(min_y, 3), round(min_z, 3)],
            "max": [round(max_x, 3), round(max_y, 3), round(max_z, 3)],
        }

    def to_scene_dict(self, elements: List[BlueprintElement]) -> Dict[str, Any]:
        """Convert elements list to Lane 3 schema-compliant dictionary."""
        scene_objects = [elem.to_3d_object(unit_scale=self.unit_scale) for elem in elements]
        scene_bounds = self.calculate_scene_bounds(elements)

        return {
            "format_version": "1.0.0",
            "scene_metadata": {
                "generator": "Lane2-OOP-Model",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "target_units": self.target_units,
                "element_count": len(elements),
                "scene_bounds": scene_bounds,
            },
            "objects": scene_objects,
        }

    def export_to_file(
        self,
        elements: List[BlueprintElement],
        output_file_path: Union[str, Path],
        indent: int = 2,
    ) -> Path:
        """Serialize elements directly to a formatted JSON file."""
        out_path = Path(output_file_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        scene_dict = self.to_scene_dict(elements)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(scene_dict, f, indent=indent)

        return out_path
