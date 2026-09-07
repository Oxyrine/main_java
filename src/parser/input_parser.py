"""Parser that converts Lane 1 data (JSON or CSV) into typed BlueprintElement domain objects."""

import csv
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, Union

from src.models import (
    BlueprintElement,
    Chair,
    Door,
    GenericFurniture,
    Table,
    Vector3D,
    Wall,
    Window,
)


class BlueprintParser:
    """
    Parses CAD extraction data into an Object-Oriented model hierarchy.
    Supports polymorphic instantiation via a type registry and provides
    heuristic inferencing for untyped legacy CSVs.
    """

    # Polymorphic class registry
    _TYPE_REGISTRY: Dict[str, Type[BlueprintElement]] = {
        "wall": Wall,
        "walls": Wall,
        "door": Door,
        "doors": Door,
        "window": Window,
        "windows": Window,
        "table": Table,
        "desk": Table,
        "chair": Chair,
        "furniture": GenericFurniture,
    }

    def __init__(self, default_units: str = "mm") -> None:
        self.default_units = default_units

    @classmethod
    def register_element_type(cls, type_name: str, element_class: Type[BlueprintElement]) -> None:
        """Register a new element type dynamically."""
        cls._TYPE_REGISTRY[type_name.lower()] = element_class

    @classmethod
    def infer_type_from_scale(cls, scale: Vector3D) -> str:
        """
        Heuristic fallback when the input table has no element-type column.
        Distinguishes walls, doors, tables, and chairs based on geometric proportions.
        """
        sx, sy, sz = abs(scale.x), abs(scale.y), abs(scale.z)

        # High aspect ratio in 2D plane (thin along one axis and long along another) -> likely Wall
        if (sx > 1500.0 and sy <= 400.0) or (sy > 1500.0 and sx <= 400.0):
            return "wall"

        # Standard door dimensions (approx 700mm - 1200mm width, standard thickness)
        if (700.0 <= sx <= 1200.0 and sy <= 400.0) or (700.0 <= sy <= 1200.0 and sx <= 400.0):
            return "door"

        # Compact square/round footprint (approx 400mm - 700mm) -> Chair
        if 350.0 <= sx <= 700.0 and 350.0 <= sy <= 700.0:
            return "chair"

        # Medium to large rectangular footprint -> Table / Furniture
        if 800.0 <= sx <= 3000.0 and 600.0 <= sy <= 2000.0:
            return "table"

        return "furniture"

    def create_element(
        self,
        element_id: str,
        element_type: Optional[str],
        position: Vector3D,
        scale: Vector3D,
        rotation: Optional[Vector3D] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> BlueprintElement:
        """Polymorphic factory instantiation based on type string."""
        normalized_type = (element_type or "").strip().lower()

        # If type is unspecified or unknown, trigger heuristic inference
        if not normalized_type:
            normalized_type = self.infer_type_from_scale(scale)

        cls = self._TYPE_REGISTRY.get(normalized_type, GenericFurniture)
        if cls is GenericFurniture:
            return GenericFurniture(
                element_id=element_id,
                type_name=normalized_type or "furniture",
                position=position,
                scale=scale,
                rotation=rotation,
                properties=properties,
            )
        return cls(
            element_id=element_id,
            position=position,
            scale=scale,
            rotation=rotation,
            properties=properties,
        )

    def parse_json_dict(self, data: Dict[str, Any]) -> List[BlueprintElement]:
        """Parse dictionary loaded from Lane 1 JSON."""
        elements_data = data.get("elements", [])
        elements: List[BlueprintElement] = []

        for item in elements_data:
            pos_dict = item.get("position", {})
            scale_dict = item.get("scale", {})
            rot_dict = item.get("rotation", {})

            pos = Vector3D(
                float(pos_dict.get("x", 0.0)),
                float(pos_dict.get("y", 0.0)),
                float(pos_dict.get("z", 0.0)),
            )
            scale = Vector3D(
                float(scale_dict.get("x", 1.0)),
                float(scale_dict.get("y", 1.0)),
                float(scale_dict.get("z", 1.0)),
            )
            rot = Vector3D(
                float(rot_dict.get("x", 0.0)),
                float(rot_dict.get("y", 0.0)),
                float(rot_dict.get("z", 0.0)),
            )

            elem = self.create_element(
                element_id=str(item.get("id", f"elem_{len(elements)+1}")),
                element_type=item.get("type"),
                position=pos,
                scale=scale,
                rotation=rot,
                properties=item.get("properties"),
            )
            elements.append(elem)

        return elements

    def parse_csv_file(self, file_path: Union[str, Path]) -> List[BlueprintElement]:
        """Parse Lane 1 tabular CSV file (supports typed and legacy untyped CAD extractions)."""
        elements: List[BlueprintElement] = []
        path = Path(file_path)

        with open(path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader, start=1):
                # Clean header keys
                cleaned = {k.strip(): v.strip() for k, v in row.items() if k is not None}

                element_id = cleaned.get("id") or f"elem_{idx}"
                element_type = cleaned.get("type")

                # Handle case-insensitive and varying column formats
                px = float(cleaned.get("Position X") or cleaned.get("position_x") or 0.0)
                py = float(cleaned.get("Position Y") or cleaned.get("position_y") or 0.0)
                pz = float(cleaned.get("Position Z") or cleaned.get("position_z") or 0.0)

                sx = float(cleaned.get("Scale X") or cleaned.get("scale_x") or 1.0)
                sy = float(cleaned.get("Scale Y") or cleaned.get("scale_y") or 1.0)
                sz = float(cleaned.get("Scale Z") or cleaned.get("scale_z") or 1.0)

                rx = float(cleaned.get("Rotation X") or cleaned.get("rotation_x") or 0.0)
                ry = float(cleaned.get("Rotation Y") or cleaned.get("rotation_y") or 0.0)
                rz = float(cleaned.get("Rotation Z") or cleaned.get("rotation_z") or 0.0)

                pos = Vector3D(px, py, pz)
                scale = Vector3D(sx, sy, sz)
                rot = Vector3D(rx, ry, rz)

                elem = self.create_element(
                    element_id=element_id,
                    element_type=element_type,
                    position=pos,
                    scale=scale,
                    rotation=rot,
                )
                elements.append(elem)

        return elements

    def parse_file(self, file_path: Union[str, Path]) -> List[BlueprintElement]:
        """Automatic file detection and parsing (JSON or CSV)."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {path}")

        suffix = path.suffix.lower()
        if suffix == ".json":
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return self.parse_json_dict(data)
        elif suffix in [".csv", ".txt"]:
            return self.parse_csv_file(path)
        else:
            raise ValueError(f"Unsupported file format: {suffix}. Supported: .json, .csv")
