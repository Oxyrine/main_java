"""
FloorPlanVisionExtractor: orchestrates image preprocessing, wall/room/opening detection,
scale estimation, room labeling, and outputs the Lane 1 extraction schema dictionary.
"""

from __future__ import annotations
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from src.vision.config import VisionConfig
from src.vision.preprocess import ImagePreprocessor, PreparedImage
from src.vision.wall_detector import WallDetector
from src.vision.room_detector import RoomDetector
from src.vision.opening_detector import OpeningDetector
from src.vision.scale_estimator import ScaleEstimator
from src.vision.ocr_labeler import RoomLabeler
from src.vision.overlay import DebugOverlay
from src.vision.geometry import Segment


class FloorPlanVisionExtractor:
    """End-to-end computer vision extractor for 2D floor plans."""

    def __init__(self, config: Optional[VisionConfig] = None):
        self.config = config or VisionConfig()
        self.preprocessor = ImagePreprocessor(max_dim=self.config.working_max_dim)
        self.wall_detector = WallDetector()
        self.room_detector = RoomDetector()
        self.opening_detector = OpeningDetector()
        self.scale_estimator = ScaleEstimator()
        self.room_labeler = RoomLabeler()
        self.overlay = DebugOverlay()

    def extract(self, image_path: Path | str, config: Optional[VisionConfig] = None) -> Dict[str, Any]:
        """
        Processes a floor-plan image and returns Lane 1 schema-compliant dictionary.
        """
        cfg = config or self.config
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Floor-plan image not found: {path}")

        # Stage 0: Preprocess (deskew, crop, downscale)
        prep = self.preprocessor.run(path)

        # Stage 1 & 2: Wall Detection & Vectorization
        walls, wall_mask, thin_mask, t_est_px = self.wall_detector.detect(prep, free_angle=cfg.free_angle)

        # Stage 3: Room Detection & Exterior Classification
        rooms, outside_mask, wall_exterior_map = self.room_detector.detect(wall_mask, walls)

        # Stage 4: Opening Detection (Doors & Windows)
        openings = self.opening_detector.detect(
            walls=walls,
            wall_mask=wall_mask,
            thin_mask=thin_mask,
            wall_exterior_map=wall_exterior_map,
        )

        # Stage 5: Scale Estimation
        building_width_px = float(prep.working_w)
        if walls:
            all_x = [w.p1.x for w in walls] + [w.p2.x for w in walls]
            if all_x:
                building_width_px = max(100.0, max(all_x) - min(all_x))

        scale_est = self.scale_estimator.estimate(openings, building_width_px, cfg)
        mm_per_px = scale_est.mm_per_px

        # Stage 6: Room Labeling (OCR + Heuristics)
        self.room_labeler.label(rooms, thin_mask, enable_ocr=cfg.enable_ocr, bgr_image=prep.bgr)

        # Optional Debug Overlay
        if cfg.debug_overlay_path:
            self.overlay.render(prep, walls, rooms, openings, cfg.debug_overlay_path)

        # Convert to Lane 1 Schema Elements
        elements: List[Dict[str, Any]] = []
        elem_counter = 1
        wh = float(prep.working_h)

        # 1. Convert Walls
        for idx, wall in enumerate(walls):
            is_ext = wall_exterior_map.get(idx, False)
            t_mm = max(cfg.default_wall_thickness_mm, wall.thickness * mm_per_px)
            h_mm = cfg.default_wall_height_mm

            if wall.is_horizontal(tol_deg=10.0):
                x0 = min(wall.p1.x, wall.p2.x) * mm_per_px
                x1 = max(wall.p1.x, wall.p2.x) * mm_per_px
                yc = (wall.p1.y + wall.p2.y) / 2.0
                y_center = (wh - yc) * mm_per_px
                w_mm = max(100.0, x1 - x0)

                elements.append({
                    "id": f"wall_{elem_counter:03d}",
                    "type": "wall",
                    "position": {"x": round(x0, 2), "y": round(y_center - t_mm / 2.0, 2), "z": 0.0},
                    "scale": {"x": round(w_mm, 2), "y": round(t_mm, 2), "z": round(h_mm, 2)},
                    "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "properties": {
                        "exterior": is_ext,
                        "orientation": "horizontal",
                        "layer": "A-WALL-EXTR" if is_ext else "A-WALL-INTR"
                    }
                })
            elif wall.is_vertical(tol_deg=10.0):
                y0 = min(wall.p1.y, wall.p2.y)
                y1 = max(wall.p1.y, wall.p2.y)
                xc = (wall.p1.x + wall.p2.x) / 2.0
                x_center = xc * mm_per_px
                # In Y-flipped coords: y1 is larger row -> smaller Y in mm
                y_min = (wh - y1) * mm_per_px
                d_mm = max(100.0, (y1 - y0) * mm_per_px)

                elements.append({
                    "id": f"wall_{elem_counter:03d}",
                    "type": "wall",
                    "position": {"x": round(x_center - t_mm / 2.0, 2), "y": round(y_min, 2), "z": 0.0},
                    "scale": {"x": round(t_mm, 2), "y": round(d_mm, 2), "z": round(h_mm, 2)},
                    "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "properties": {
                        "exterior": is_ext,
                        "orientation": "vertical",
                        "layer": "A-WALL-EXTR" if is_ext else "A-WALL-INTR"
                    }
                })
            else:
                # Angled wall
                length_mm = wall.length * mm_per_px
                cx_mm = ((wall.p1.x + wall.p2.x) / 2.0) * mm_per_px
                cy_mm = (wh - (wall.p1.y + wall.p2.y) / 2.0) * mm_per_px
                # Y is inverted in image vs Cartesian
                cart_angle_deg = -math.degrees(math.atan2(wall.dy, wall.dx)) % 360.0

                elements.append({
                    "id": f"wall_{elem_counter:03d}",
                    "type": "wall",
                    "position": {"x": round(cx_mm - length_mm / 2.0, 2), "y": round(cy_mm - t_mm / 2.0, 2), "z": 0.0},
                    "scale": {"x": round(length_mm, 2), "y": round(t_mm, 2), "z": round(h_mm, 2)},
                    "rotation": {"x": 0.0, "y": 0.0, "z": round(cart_angle_deg, 2)},
                    "properties": {
                        "exterior": is_ext,
                        "orientation": "angled",
                        "layer": "A-WALL-EXTR" if is_ext else "A-WALL-INTR"
                    }
                })
            elem_counter += 1

        # 2. Convert Openings (Doors and Windows)
        for op in openings:
            # Determine orientation directly from opening gap endpoints
            is_horiz = abs(op.p1.y - op.p2.y) <= abs(op.p1.x - op.p2.x)
            t_mm = cfg.default_wall_thickness_mm

            if op.kind == "door":
                # Physical validation: residential doors are 600mm to 2000mm wide (single or double doors).
                # Gaps wider than 2200mm are open room passages or wall discontinuities; skip solid door leaf.
                gap_span_mm = (abs(op.p1.x - op.p2.x) if is_horiz else abs(op.p1.y - op.p2.y)) * mm_per_px
                if gap_span_mm > 2200.0:
                    continue
                h_mm = cfg.default_door_height_mm
                z_pos = 0.0
            else:
                h_mm = cfg.default_window_height_mm
                z_pos = cfg.default_window_sill_mm

            if is_horiz:
                x0 = min(op.p1.x, op.p2.x) * mm_per_px
                x1 = max(op.p1.x, op.p2.x) * mm_per_px
                yc = (op.p1.y + op.p2.y) / 2.0
                y_center = (wh - yc) * mm_per_px
                w_mm = max(200.0, x1 - x0)
                pos = {"x": round(x0, 2), "y": round(y_center - t_mm / 2.0, 2), "z": round(z_pos, 2)}
                scale = {"x": round(w_mm, 2), "y": round(t_mm, 2), "z": round(h_mm, 2)}
            else:
                y0 = min(op.p1.y, op.p2.y)
                y1 = max(op.p1.y, op.p2.y)
                xc = (op.p1.x + op.p2.x) / 2.0
                x_center = xc * mm_per_px
                y_min = (wh - y1) * mm_per_px
                d_mm = max(200.0, (y1 - y0) * mm_per_px)
                pos = {"x": round(x_center - t_mm / 2.0, 2), "y": round(y_min, 2), "z": round(z_pos, 2)}
                scale = {"x": round(t_mm, 2), "y": round(d_mm, 2), "z": round(h_mm, 2)}

            elements.append({
                "id": f"{op.kind}_{elem_counter:03d}",
                "type": op.kind,
                "position": pos,
                "scale": scale,
                "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
                "properties": {
                    "exterior": op.is_exterior,
                    "swing_radius_mm": round(op.arc_radius_px * mm_per_px, 2) if op.arc_radius_px else None,
                    "layer": "A-DOOR" if op.kind == "door" else "A-GLAZ"
                }
            })
            elem_counter += 1

        # 3. Convert Rooms to Floor Slabs
        for r in rooms:
            rx, ry, rw, rh = r.bbox
            min_x = rx * mm_per_px
            min_y = (wh - (ry + rh)) * mm_per_px
            w_mm = rw * mm_per_px
            d_mm = rh * mm_per_px
            floor_thick = cfg.default_floor_thickness_mm
            area_m2 = round((r.area_px * (mm_per_px ** 2)) / 1_000_000.0, 2)

            elements.append({
                "id": f"floor_{elem_counter:03d}",
                "type": "floor",
                "position": {"x": round(min_x, 2), "y": round(min_y, 2), "z": 0.0},
                "scale": {"x": round(w_mm, 2), "y": round(d_mm, 2), "z": round(floor_thick, 2)},
                "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
                "properties": {
                    "room_id": r.id,
                    "room_type": r.room_type,
                    "label": r.label,
                    "area_m2": area_m2,
                    "layer": "A-FLOR"
                }
            })
            elem_counter += 1

            # 4. Contextual Furniture Placement based on Room Type
            cx_mm = r.centroid[0] * mm_per_px
            cy_mm = (wh - r.centroid[1]) * mm_per_px

            if r.room_type in ("living", "dining", "room") and area_m2 >= 6.0:
                # Add table at room center
                elements.append({
                    "id": f"table_{elem_counter:03d}",
                    "type": "table",
                    "position": {"x": round(cx_mm - 600.0, 2), "y": round(cy_mm - 400.0, 2), "z": 0.0},
                    "scale": {"x": 1200.0, "y": 800.0, "z": 750.0},
                    "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "properties": {"room_type": r.room_type, "layer": "I-FURN-TABL"}
                })
                elem_counter += 1

                # Add chair next to table
                elements.append({
                    "id": f"chair_{elem_counter:03d}",
                    "type": "chair",
                    "position": {"x": round(cx_mm + 700.0, 2), "y": round(cy_mm - 250.0, 2), "z": 0.0},
                    "scale": {"x": 500.0, "y": 500.0, "z": 900.0},
                    "rotation": {"x": 0.0, "y": 0.0, "z": 180.0},
                    "properties": {"room_type": r.room_type, "layer": "I-FURN-CHAI"}
                })
                elem_counter += 1

            elif r.room_type == "bedroom" and area_m2 >= 5.0:
                # Add bed in bedroom
                elements.append({
                    "id": f"table_{elem_counter:03d}",
                    "type": "table",
                    "position": {"x": round(cx_mm - 800.0, 2), "y": round(cy_mm - 1000.0, 2), "z": 0.0},
                    "scale": {"x": 1600.0, "y": 2000.0, "z": 550.0},
                    "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "properties": {"room_type": "bedroom", "furniture_type": "bed", "layer": "I-FURN-BED"}
                })
                elem_counter += 1

            elif r.room_type == "sauna":
                # Add sauna bench
                elements.append({
                    "id": f"table_{elem_counter:03d}",
                    "type": "table",
                    "position": {"x": round(cx_mm - 300.0, 2), "y": round(cy_mm - 500.0, 2), "z": 0.0},
                    "scale": {"x": 600.0, "y": 1000.0, "z": 450.0},
                    "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "properties": {"room_type": "sauna", "furniture_type": "bench", "layer": "I-FURN-BNCH"}
                })
                elem_counter += 1

        return {
            "version": "1.0.0",
            "units": "mm",
            "metadata": {
                "source_file": str(path),
                "extracted_at": datetime.now(timezone.utc).isoformat(),
                "entity_count": len(elements),
                "resolution": f"{prep.orig_w}x{prep.orig_h}",
                "scale_inference": {
                    "mm_per_px": round(scale_est.mm_per_px, 4),
                    "method": scale_est.method,
                    "confidence": scale_est.confidence
                },
                "cv_stats": {
                    "wall_count": len(walls),
                    "room_count": len(rooms),
                    "opening_count": len(openings)
                }
            },
            "elements": elements
        }
