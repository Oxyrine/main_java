"""Lane 1: CAD Blueprint Extractor for DXF files.

Parses AutoCAD DXF files (ASCII format) and extracts lines, polylines, blocks,
and annotations into typed, structured blueprint element records.
Produces output conforming to schemas/lane1_input_schema.json.
"""

from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


class CadExtractor:
    """
    Parses CAD blueprint files (.dxf) and produces typed element coordinates.
    Extracts geometric entities, classifies element types by CAD layer or block name,
    and computes positions, scales, and rotation angles.
    """

    # Semantic layer classification mappings (case-insensitive substrings)
    LAYER_TYPE_MAP = {
        "wall": "wall",
        "mur": "wall",
        "pared": "wall",
        "partition": "wall",
        "door": "door",
        "porte": "door",
        "puerta": "door",
        "window": "window",
        "fenetre": "window",
        "glaz": "window",
        "chair": "chair",
        "seat": "chair",
        "table": "table",
        "desk": "table",
        "furn": "furniture",
        "mob": "furniture",
    }

    # Default architectural dimensions (in millimetres)
    DEFAULT_WALL_HEIGHT = 2800.0
    DEFAULT_WALL_THICKNESS = 200.0
    DEFAULT_DOOR_HEIGHT = 2100.0
    DEFAULT_WINDOW_HEIGHT = 1200.0
    DEFAULT_SILL_HEIGHT = 900.0

    def __init__(self, units: str = "mm") -> None:
        self.units = units

    def classify_layer(self, layer_name: str, entity_name: str = "", entity_type: str = "") -> str:
        """Classifies element type based on CAD layer name or entity/block name."""
        combined = f"{layer_name} {entity_name}".lower()
        for key, elem_type in self.LAYER_TYPE_MAP.items():
            if key in combined:
                return elem_type
        # If entity is a linear or polyline geometric entity (LINE, LWPOLYLINE, POLYLINE),
        # and the layer is generic (e.g. "0", "Defpoints", "Plan"), default to "wall"
        if entity_type.upper() in ["LINE", "LWPOLYLINE", "POLYLINE", "ARC"]:
            return "wall"
        return "furniture"

    def _parse_dxf_tag_pairs(self, text: str) -> List[Tuple[int, str]]:
        """Parses raw ASCII DXF text into a flat list of (group_code, value) pairs."""
        lines = text.splitlines()
        pairs: List[Tuple[int, str]] = []
        i = 0
        while i < len(lines) - 1:
            code_line = lines[i].strip()
            val_line = lines[i + 1].strip()
            try:
                code = int(code_line)
                pairs.append((code, val_line))
                i += 2
            except ValueError:
                i += 1
        return pairs

    def parse_dxf_string(self, dxf_content: str, filename: str = "blueprint.dxf") -> Dict[str, Any]:
        """Parses DXF content string and returns schema-compliant Lane 1 JSON payload."""
        pairs = self._parse_dxf_tag_pairs(dxf_content)
        elements: List[Dict[str, Any]] = []

        # Auto-detect coordinate units:
        # Scan coordinate values to determine if the drawing is in meters (< 150) or millimeters
        coord_vals = []
        for code, val in pairs:
            if code in (10, 11, 20, 21):
                try:
                    coord_vals.append(abs(float(val)))
                except ValueError:
                    pass
        max_coord = max(coord_vals) if coord_vals else 1000.0
        unit_mult = 1000.0 if (0.0 < max_coord < 150.0) else 1.0

        in_entities_section = False
        i = 0
        n = len(pairs)
        entity_count = 0

        while i < n:
            code, val = pairs[i]

            # Detect ENTITIES section
            if code == 0 and val == "SECTION":
                if i + 1 < n and pairs[i + 1] == (2, "ENTITIES"):
                    in_entities_section = True
                    i += 2
                    continue
            elif code == 0 and val == "ENDSEC":
                in_entities_section = False

            if in_entities_section and code == 0:
                entity_type = val.upper()
                entity_tags: Dict[int, List[str]] = {}
                i += 1

                if entity_type == "POLYLINE":
                    # Traditional AutoCAD POLYLINE with child VERTEX entities
                    while i < n and pairs[i] != (0, "SEQEND") and pairs[i][0] != 0:
                        c_tag, v_tag = pairs[i]
                        entity_tags.setdefault(c_tag, []).append(v_tag)
                        i += 1
                    vx, vy = [], []
                    while i < n and pairs[i] != (0, "SEQEND"):
                        if pairs[i] == (0, "VERTEX"):
                            i += 1
                            v_tags: Dict[int, List[str]] = {}
                            while i < n and pairs[i][0] != 0:
                                v_tags.setdefault(pairs[i][0], []).append(pairs[i][1])
                                i += 1
                            if 10 in v_tags and 20 in v_tags:
                                vx.append(float(v_tags[10][0]))
                                vy.append(float(v_tags[20][0]))
                        else:
                            i += 1
                    if i < n and pairs[i] == (0, "SEQEND"):
                        i += 1
                    entity_tags[10] = [str(x) for x in vx]
                    entity_tags[20] = [str(y) for y in vy]
                    entity_type = "LWPOLYLINE"
                else:
                    while i < n and pairs[i][0] != 0:
                        c_tag, v_tag = pairs[i]
                        entity_tags.setdefault(c_tag, []).append(v_tag)
                        i += 1

                # Process specific CAD entities
                parsed_elem = self._convert_entity(entity_type, entity_tags, entity_count + 1, unit_mult=unit_mult)
                if parsed_elem:
                    if isinstance(parsed_elem, list):
                        elements.extend(parsed_elem)
                        entity_count += len(parsed_elem)
                    else:
                        elements.append(parsed_elem)
                        entity_count += 1
                continue

            i += 1

        return {
            "version": "1.0.0",
            "units": self.units,
            "metadata": {
                "source_file": filename,
                "extracted_at": datetime.now(timezone.utc).isoformat(),
                "entity_count": len(elements),
            },
            "elements": elements,
        }

    def _convert_entity(
        self, entity_type: str, tags: Dict[int, List[str]], elem_idx: int, unit_mult: float = 1.0
    ) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        """Converts raw DXF entity tags into standardized BlueprintElement records."""
        layer = tags.get(8, ["0"])[0]

        if entity_type == "LINE":
            # LINE endpoints: (10,20,30) and (11,21,31)
            x1 = float(tags.get(10, [0.0])[0]) * unit_mult
            y1 = float(tags.get(20, [0.0])[0]) * unit_mult
            z1 = float(tags.get(30, [0.0])[0]) * unit_mult

            x2 = float(tags.get(11, [0.0])[0]) * unit_mult
            y2 = float(tags.get(21, [0.0])[0]) * unit_mult
            z2 = float(tags.get(31, [0.0])[0]) * unit_mult

            dx = x2 - x1
            dy = y2 - y1
            length = math.hypot(dx, dy)
            if length < 1.0:
                return None

            angle_deg = math.degrees(math.atan2(dy, dx))
            elem_type = self.classify_layer(layer, entity_type="LINE")

            # Determine thickness and height based on type
            if elem_type == "wall":
                thickness = self.DEFAULT_WALL_THICKNESS
                height = self.DEFAULT_WALL_HEIGHT
            elif elem_type == "door":
                thickness = self.DEFAULT_WALL_THICKNESS
                height = self.DEFAULT_DOOR_HEIGHT
            elif elem_type == "window":
                thickness = self.DEFAULT_WALL_THICKNESS
                height = self.DEFAULT_WINDOW_HEIGHT
            else:
                thickness = 100.0
                height = 500.0

            return {
                "id": f"{elem_type}_{elem_idx:03d}",
                "type": elem_type,
                "position": {"x": round(x1, 2), "y": round(y1, 2), "z": round(z1, 2)},
                "scale": {"x": round(length, 2), "y": round(thickness, 2), "z": round(height, 2)},
                "rotation": {"x": 0.0, "y": 0.0, "z": round(angle_deg, 2)},
                "properties": {
                    "layer": layer,
                    "cad_entity": "LINE",
                    "length": round(length, 2),
                },
            }

        elif entity_type in ["INSERT", "BLOCK"]:
            # Block insertions (doors, windows, furniture symbols)
            block_name = tags.get(2, ["unknown"])[0]
            x = float(tags.get(10, [0.0])[0]) * unit_mult
            y = float(tags.get(20, [0.0])[0]) * unit_mult
            z = float(tags.get(30, [0.0])[0]) * unit_mult

            sx = float(tags.get(41, [1.0])[0])
            sy = float(tags.get(42, [1.0])[0])
            sz = float(tags.get(43, [1.0])[0])
            rot = float(tags.get(50, [0.0])[0])

            elem_type = self.classify_layer(layer, entity_name=block_name, entity_type="INSERT")

            # Assign typical physical dimensions if block scale is nominal (e.g. 1.0)
            if abs(sx) <= 2.0 and abs(sy) <= 2.0:
                if elem_type == "chair":
                    dims = (500.0, 500.0, 900.0)
                elif elem_type == "table":
                    dims = (1400.0, 800.0, 750.0)
                elif elem_type == "door":
                    dims = (900.0, 200.0, 2100.0)
                elif elem_type == "window":
                    dims = (1200.0, 200.0, 1200.0)
                else:
                    dims = (600.0, 600.0, 600.0)
            else:
                dims = (abs(sx) * unit_mult, abs(sy) * unit_mult, abs(sz) * unit_mult if abs(sz) > 10.0 else 800.0)

            return {
                "id": f"{elem_type}_{elem_idx:03d}",
                "type": elem_type,
                "position": {"x": round(x, 2), "y": round(y, 2), "z": round(z, 2)},
                "scale": {"x": round(dims[0], 2), "y": round(dims[1], 2), "z": round(dims[2], 2)},
                "rotation": {"x": 0.0, "y": 0.0, "z": round(rot, 2)},
                "properties": {
                    "layer": layer,
                    "block_name": block_name,
                    "cad_entity": "INSERT",
                },
            }

        elif entity_type == "LWPOLYLINE":
            # Polyline segments: break into individual wall segments connecting consecutive vertices
            xs = [float(v) * unit_mult for v in tags.get(10, [])]
            ys = [float(v) * unit_mult for v in tags.get(20, [])]
            flags = int(tags.get(70, [0])[0]) if tags.get(70) else 0
            is_closed = bool(flags & 1)

            elem_type = self.classify_layer(layer, entity_type="LWPOLYLINE")
            thickness = self.DEFAULT_WALL_THICKNESS if elem_type == "wall" else (
                self.DEFAULT_WALL_THICKNESS if elem_type in ["door", "window"] else 100.0
            )
            height = self.DEFAULT_WALL_HEIGHT if elem_type == "wall" else (
                self.DEFAULT_DOOR_HEIGHT if elem_type == "door" else (
                    self.DEFAULT_WINDOW_HEIGHT if elem_type == "window" else 800.0
                )
            )

            poly_elems: List[Dict[str, Any]] = []
            num_pts = min(len(xs), len(ys))
            if num_pts >= 2:
                indices = list(range(num_pts - 1))
                if is_closed and num_pts > 2:
                    indices.append(num_pts - 1)

                for sub_idx in indices:
                    next_idx = (sub_idx + 1) % num_pts
                    x1, y1 = xs[sub_idx], ys[sub_idx]
                    x2, y2 = xs[next_idx], ys[next_idx]
                    dx = x2 - x1
                    dy = y2 - y1
                    length = math.hypot(dx, dy)
                    if length < 1.0:
                        continue
                    angle_deg = math.degrees(math.atan2(dy, dx))
                    poly_elems.append({
                        "id": f"{elem_type}_{elem_idx + len(poly_elems):03d}",
                        "type": elem_type,
                        "position": {"x": round(x1, 2), "y": round(y1, 2), "z": 0.0},
                        "scale": {"x": round(length, 2), "y": round(thickness, 2), "z": round(height, 2)},
                        "rotation": {"x": 0.0, "y": 0.0, "z": round(angle_deg, 2)},
                        "properties": {
                            "layer": layer,
                            "cad_entity": "LWPOLYLINE",
                            "length": round(length, 2),
                        },
                    })
                return poly_elems

        return None

    def extract_image(
        self,
        image_path: Union[str, Path],
        building_width_mm: float = 12000.0,
        vision_config: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Extracts walls, rooms, openings, and scale from a 2D raster floor plan image (PNG/JPG).
        Delegates to the OpenCV-based FloorPlanVisionExtractor pipeline.
        """
        from src.vision.config import VisionConfig
        from src.vision.floorplan_vision import FloorPlanVisionExtractor

        cfg = vision_config
        if cfg is None:
            cfg = VisionConfig(known_width_mm=building_width_mm)
        extractor = FloorPlanVisionExtractor(config=cfg)
        return extractor.extract(image_path, config=cfg)

    def extract_file(
        self,
        file_path: Union[str, Path],
        vision_config: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Extracts elements from a DXF or Image file on disk."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"CAD/Blueprint file not found: {path}")

        suffix = path.suffix.lower()
        if suffix in [".png", ".jpg", ".jpeg", ".bmp", ".webp"]:
            return self.extract_image(path, vision_config=vision_config)

        # Try reading as UTF-8 or fallback to latin-1 for DXF
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(path, "r", encoding="latin-1") as f:
                content = f.read()

        return self.parse_dxf_string(content, filename=path.name)

    def export_to_json_file(self, extracted_data: Dict[str, Any], output_path: Union[str, Path]) -> Path:
        """Saves extracted elements to a schema-compliant JSON file."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(extracted_data, f, indent=2)
        return out
