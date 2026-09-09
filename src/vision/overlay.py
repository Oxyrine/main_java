"""
Debug overlay rendering: visualizes detected walls, rooms, openings, and swing arcs.
"""

from __future__ import annotations
import math
from pathlib import Path
from typing import List
import numpy as np

from src.vision.geometry import Segment
from src.vision.preprocess import PreparedImage
from src.vision.room_detector import RoomRegion
from src.vision.opening_detector import Opening


class DebugOverlay:
    """Renders debug visualizations of vector elements atop the floor plan."""

    def render(
        self,
        prepared: PreparedImage,
        walls: List[Segment],
        rooms: List[RoomRegion],
        openings: List[Opening],
        out_path: Path | str
    ) -> Path:
        """Draws detected architectural features onto the preprocessed image."""
        import cv2

        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        vis = prepared.bgr.copy()
        # Dim base image slightly
        vis = cv2.addWeighted(vis, 0.6, np.full_like(vis, 255), 0.4, 0)

        # 1. Draw Rooms (semi-transparent polygons and centroids)
        overlay = vis.copy()
        for r in rooms:
            if r.polygon and len(r.polygon) >= 3:
                pts = np.array(r.polygon, dtype=np.int32).reshape((-1, 1, 2))
                cv2.fillPoly(overlay, [pts], (230, 240, 255))
                cv2.polylines(overlay, [pts], True, (180, 190, 220), 2)
            else:
                x, y, w, h = [int(v) for v in r.bbox]
                cv2.rectangle(overlay, (x, y), (x + w, y + h), (230, 240, 255), -1)

        cv2.addWeighted(overlay, 0.4, vis, 0.6, 0, vis)

        # Room labels
        font = cv2.FONT_HERSHEY_SIMPLEX
        for r in rooms:
            cx, cy = int(round(r.centroid[0])), int(round(r.centroid[1]))
            lbl = f"{r.label} ({r.room_type})" if r.label else r.id
            cv2.putText(vis, lbl, (cx - 40, cy), font, 0.5, (60, 40, 180), 1, cv2.LINE_AA)

        # 2. Draw Walls (Green with thickness)
        for w in walls:
            p1 = (int(round(w.p1.x)), int(round(w.p1.y)))
            p2 = (int(round(w.p2.x)), int(round(w.p2.y)))
            thick = max(2, int(round(w.thickness)))
            cv2.line(vis, p1, p2, (0, 180, 0), thick)

        # 3. Draw Openings (Doors in Blue, Windows in Cyan)
        for op in openings:
            p1 = (int(round(op.p1.x)), int(round(op.p1.y)))
            p2 = (int(round(op.p2.x)), int(round(op.p2.y)))
            if op.kind == "door":
                # Blue line across opening
                cv2.line(vis, p1, p2, (255, 100, 0), 4)
                if op.hinge_px and op.arc_radius_px:
                    hx, hy = int(round(op.hinge_px.x)), int(round(op.hinge_px.y))
                    rad = int(round(op.arc_radius_px))
                    cv2.circle(vis, (hx, hy), 4, (200, 0, 200), -1)
                    cv2.circle(vis, (hx, hy), rad, (200, 0, 200), 1)
            else:
                # Cyan line across window
                cv2.line(vis, p1, p2, (0, 220, 255), 4)

        cv2.imwrite(str(out_path), vis)
        return out_path
