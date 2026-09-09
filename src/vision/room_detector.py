"""
Room detection stage: topological flood-filling, connected components,
room polygon extraction, and exterior wall classification.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
import numpy as np

from src.vision.geometry import Segment, Point


@dataclass
class RoomRegion:
    """Represents a detected architectural room."""
    id: str
    bbox: Tuple[float, float, float, float]  # (x, y, w, h) in working px
    centroid: Tuple[float, float]           # (cx, cy) in working px
    area_px: float
    polygon: List[Tuple[float, float]] = field(default_factory=list)
    label: Optional[str] = None
    room_type: str = "generic"


class RoomDetector:
    """Extracts enclosed interior rooms and classifies exterior walls."""

    def __init__(self, min_area_px: float = 1000.0):
        self.min_area_px = min_area_px

    def detect(
        self,
        wall_mask: np.ndarray,
        walls: List[Segment]
    ) -> Tuple[List[RoomRegion], np.ndarray, Dict[int, bool]]:
        """
        Extracts interior room regions and exterior wall classifications.
        Returns:
            (rooms, outside_mask, wall_exterior_map)
        """
        import cv2

        h, w = wall_mask.shape[:2]

        # 1. Create sealed wall mask by drawing detected walls and bridging collinear opening gaps
        sealed = wall_mask.copy()
        for wall in walls:
            t = max(16, int(round(wall.thickness * 1.2)))
            p1 = (int(round(wall.p1.x)), int(round(wall.p1.y)))
            p2 = (int(round(wall.p2.x)), int(round(wall.p2.y)))
            cv2.line(sealed, p1, p2, 255, t)

        # Bridge collinear gaps between horizontal walls
        horiz = [w for w in walls if w.is_horizontal(tol_deg=10.0)]
        for i, w1 in enumerate(horiz):
            for j, w2 in enumerate(horiz):
                if i >= j:
                    continue
                y1 = (w1.p1.y + w1.p2.y) / 2.0
                y2 = (w2.p1.y + w2.p2.y) / 2.0
                if abs(y1 - y2) <= max(20.0, max(w1.thickness, w2.thickness) * 1.5):
                    x1_max = max(w1.p1.x, w1.p2.x)
                    x2_min = min(w2.p1.x, w2.p2.x)
                    if x1_max > x2_min:
                        x1_max, x2_min = max(w2.p1.x, w2.p2.x), min(w1.p1.x, w1.p2.x)
                    gap = x2_min - x1_max
                    if 0 < gap < 300:
                        y = int(round((y1 + y2) / 2.0))
                        t_bridge = max(16, int(round(max(w1.thickness, w2.thickness))))
                        cv2.line(sealed, (int(round(x1_max)), y), (int(round(x2_min)), y), 255, t_bridge)

        # Bridge collinear gaps between vertical walls
        vert = [w for w in walls if w.is_vertical(tol_deg=10.0)]
        for i, w1 in enumerate(vert):
            for j, w2 in enumerate(vert):
                if i >= j:
                    continue
                x1 = (w1.p1.x + w1.p2.x) / 2.0
                x2 = (w2.p1.x + w2.p2.x) / 2.0
                if abs(x1 - x2) <= max(20.0, max(w1.thickness, w2.thickness) * 1.5):
                    y1_max = max(w1.p1.y, w1.p2.y)
                    y2_min = min(w2.p1.y, w2.p2.y)
                    if y1_max > y2_min:
                        y1_max, y2_min = max(w2.p1.y, w2.p2.y), min(w1.p1.y, w1.p2.y)
                    gap = y2_min - y1_max
                    if 0 < gap < 300:
                        x = int(round((x1 + x2) / 2.0))
                        t_bridge = max(16, int(round(max(w1.thickness, w2.thickness))))
                        cv2.line(sealed, (x, int(round(y1_max))), (x, int(round(y2_min))), 255, t_bridge)

        # Bridge T-junctions / L-corners for openings (dist <= 110px)
        for vw in vert:
            vx = (vw.p1.x + vw.p2.x) / 2.0
            for vy in [min(vw.p1.y, vw.p2.y), max(vw.p1.y, vw.p2.y)]:
                for hw in horiz:
                    hy = (hw.p1.y + hw.p2.y) / 2.0
                    hx_min = min(hw.p1.x, hw.p2.x)
                    hx_max = max(hw.p1.x, hw.p2.x)
                    if (hx_min - 25.0) <= vx <= (hx_max + 25.0):
                        dist = abs(hy - vy)
                        if 0 < dist <= 110.0:
                            cv2.line(sealed, (int(round(vx)), int(round(vy))), (int(round(vx)), int(round(hy))), 255, 16)

        for hw in horiz:
            hy = (hw.p1.y + hw.p2.y) / 2.0
            for hx in [min(hw.p1.x, hw.p2.x), max(hw.p1.x, hw.p2.x)]:
                for vw in vert:
                    vx = (vw.p1.x + vw.p2.x) / 2.0
                    vy_min = min(vw.p1.y, vw.p2.y)
                    vy_max = max(vw.p1.y, vw.p2.y)
                    if (vy_min - 25.0) <= hy <= (vy_max + 25.0):
                        dist = abs(vx - hx)
                        if 0 < dist <= 110.0:
                            cv2.line(sealed, (int(round(hx)), int(round(hy))), (int(round(vx)), int(round(hy))), 255, 16)

        # Bridge building envelope exterior corners
        if walls:
            all_x = [w.p1.x for w in walls] + [w.p2.x for w in walls]
            all_y = [w.p1.y for w in walls] + [w.p2.y for w in walls]
            min_x, max_x = min(all_x), max(all_x)
            min_y, max_y = min(all_y), max(all_y)

            for vw in vert:
                vx = (vw.p1.x + vw.p2.x) / 2.0
                if abs(vx - min_x) <= 35.0 or abs(vx - max_x) <= 35.0:
                    v_top = min(vw.p1.y, vw.p2.y)
                    v_bot = max(vw.p1.y, vw.p2.y)
                    if abs(v_top - min_y) < 220.0:
                        cv2.line(sealed, (int(round(vx)), int(round(v_top))), (int(round(vx)), int(round(min_y))), 255, 16)
                    if abs(v_bot - max_y) < 220.0:
                        cv2.line(sealed, (int(round(vx)), int(round(v_bot))), (int(round(vx)), int(round(max_y))), 255, 16)

            for hw in horiz:
                hy = (hw.p1.y + hw.p2.y) / 2.0
                if abs(hy - min_y) <= 35.0 or abs(hy - max_y) <= 35.0:
                    h_left = min(hw.p1.x, hw.p2.x)
                    h_right = max(hw.p1.x, hw.p2.x)
                    if abs(h_left - min_x) < 220.0:
                        cv2.line(sealed, (int(round(h_left)), int(round(hy))), (int(round(min_x)), int(round(hy))), 255, 16)
                    if abs(h_right - max_x) < 220.0:
                        cv2.line(sealed, (int(round(h_right)), int(round(hy))), (int(round(max_x)), int(round(hy))), 255, 16)

        # 2. Invert sealed wall mask to get free space
        free_space = cv2.bitwise_not(sealed)

        # 3. Flood fill from image borders to identify outside background
        flood = free_space.copy()
        mask = np.zeros((h + 2, w + 2), dtype=np.uint8)

        # Flood fill from all 4 borders
        border_pts = [
            (0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1),
            (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)
        ]
        for pt in border_pts:
            if flood[pt[1], pt[0]] == 255:
                cv2.floodFill(flood, mask, pt, 128)

        outside_mask = (flood == 128).astype(np.uint8) * 255
        interior_mask = ((flood == 255) & (sealed == 0)).astype(np.uint8) * 255

        # 3. Connected components on interior spaces
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(interior_mask, connectivity=8)

        rooms: List[RoomRegion] = []
        room_idx = 1
        for i in range(1, num_labels):
            area = float(stats[i, cv2.CC_STAT_AREA])
            if area < self.min_area_px:
                continue

            rx = float(stats[i, cv2.CC_STAT_LEFT])
            ry = float(stats[i, cv2.CC_STAT_TOP])
            rw = float(stats[i, cv2.CC_STAT_WIDTH])
            rh = float(stats[i, cv2.CC_STAT_HEIGHT])
            cx, cy = float(centroids[i][0]), float(centroids[i][1])

            # Ensure room centroid is not in outside_mask
            cxi = max(0, min(w - 1, int(round(cx))))
            cyi = max(0, min(h - 1, int(round(cy))))
            if outside_mask[cyi, cxi] == 255:
                continue

            # Extract simplified polygon
            comp_mask = (labels == i).astype(np.uint8) * 255
            contours, _ = cv2.findContours(comp_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            poly_pts: List[Tuple[float, float]] = []
            if contours:
                largest_c = max(contours, key=cv2.contourArea)
                epsilon = 0.015 * cv2.arcLength(largest_c, True)
                approx = cv2.approxPolyDP(largest_c, epsilon, True)
                poly_pts = [(float(pt[0][0]), float(pt[0][1])) for pt in approx]

            rooms.append(
                RoomRegion(
                    id=f"room_{room_idx:03d}",
                    bbox=(rx, ry, rw, rh),
                    centroid=(cx, cy),
                    area_px=area,
                    polygon=poly_pts,
                    room_type="room",
                )
            )
            room_idx += 1

        # 4. Classify exterior walls
        wall_exterior_map: Dict[int, bool] = {}
        for idx, wall in enumerate(walls):
            wall_exterior_map[idx] = self._is_wall_exterior(wall, outside_mask)

        return rooms, outside_mask, wall_exterior_map

    def _is_wall_exterior(self, wall: Segment, outside_mask: np.ndarray) -> bool:
        """Determines if a wall segment borders the outside exterior."""
        h, w = outside_mask.shape[:2]
        length = wall.length
        if length < 1e-4:
            return False

        nx = -wall.dy / length
        ny = wall.dx / length
        offset = max(16.0, (wall.thickness / 2.0) + 8.0)

        # Sample points along the wall on side 1 and side 2
        num_samples = max(3, int(length / 15.0))
        outside_hits = 0
        for i in range(num_samples):
            t = (i + 0.5) / num_samples
            pt = wall.point_at(t)
            # Side 1
            s1_x = int(round(pt.x + nx * offset))
            s1_y = int(round(pt.y + ny * offset))
            # Side 2
            s2_x = int(round(pt.x - nx * offset))
            s2_y = int(round(pt.y - ny * offset))

            if 0 <= s1_x < w and 0 <= s1_y < h:
                if outside_mask[s1_y, s1_x] == 255:
                    outside_hits += 1
            else:
                outside_hits += 1

            if 0 <= s2_x < w and 0 <= s2_y < h:
                if outside_mask[s2_y, s2_x] == 255:
                    outside_hits += 1
            else:
                outside_hits += 1

        return outside_hits >= 2
