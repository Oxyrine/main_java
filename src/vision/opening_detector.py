"""
Opening detection stage: wall gap walking, collinear segment gap analysis,
door swing arc detection on thin-ink mask, and door vs window classification.
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
import numpy as np

from src.vision.geometry import Point, Segment


@dataclass
class Opening:
    """Represents an architectural opening (door or window) along a wall."""
    id: str
    kind: str                      # "door" or "window"
    wall_idx: int
    p1: Point                      # Start of opening gap (working px)
    p2: Point                      # End of opening gap (working px)
    width_px: float
    hinge_px: Optional[Point] = None
    arc_radius_px: Optional[float] = None
    is_exterior: bool = False

    @property
    def center_px(self) -> Point:
        return Point((self.p1.x + self.p2.x) / 2.0, (self.p1.y + self.p2.y) / 2.0)


class OpeningDetector:
    """Detects door and window gaps along walls and classifies using swing arcs."""

    def __init__(self, min_gap_px: float = 20.0, max_gap_px: float = 180.0):
        self.min_gap_px = min_gap_px
        self.max_gap_px = max_gap_px

    def detect(
        self,
        walls: List[Segment],
        wall_mask: np.ndarray,
        thin_mask: np.ndarray,
        wall_exterior_map: Dict[int, bool],
        scale_hint_mm_per_px: Optional[float] = None
    ) -> List[Opening]:
        """
        Identifies gaps along and between walls, tests for door swing arcs in thin_mask,
        and classifies as door or window.
        """
        import cv2

        openings: List[Opening] = []
        opening_idx = 1
        h, w = wall_mask.shape[:2]

        # 1. Extract potential door arcs from thin_mask
        detected_arcs = self._find_door_arcs(thin_mask)

        # 2. Collect candidate gaps
        candidate_gaps: List[Tuple[int, Point, Point, float]] = []

        # A. Collinear gaps between horizontal walls
        horiz_walls = [(idx, wall) for idx, wall in enumerate(walls) if wall.is_horizontal(tol_deg=10.0)]
        # Cluster by Y
        y_clusters: List[List[Tuple[int, Segment]]] = []
        for idx, wall in horiz_walls:
            y_mid = (wall.p1.y + wall.p2.y) / 2.0
            placed = False
            for cl in y_clusters:
                cl_y = sum((w.p1.y + w.p2.y) / 2.0 for _, w in cl) / len(cl)
                if abs(y_mid - cl_y) <= max(12.0, wall.thickness):
                    cl.append((idx, wall))
                    placed = True
                    break
            if not placed:
                y_clusters.append([(idx, wall)])

        for cl in y_clusters:
            # Sort by x_min
            cl.sort(key=lambda item: min(item[1].p1.x, item[1].p2.x))
            avg_y = sum((w.p1.y + w.p2.y) / 2.0 for _, w in cl) / len(cl)
            for i in range(len(cl) - 1):
                idx1, w1 = cl[i]
                idx2, w2 = cl[i + 1]
                x1_max = max(w1.p1.x, w1.p2.x)
                x2_min = min(w2.p1.x, w2.p2.x)
                gap_len = x2_min - x1_max
                if self.min_gap_px <= gap_len <= self.max_gap_px:
                    candidate_gaps.append((
                        idx1,
                        Point(x1_max, avg_y),
                        Point(x2_min, avg_y),
                        gap_len
                    ))

        # B. Collinear gaps between vertical walls
        vert_walls = [(idx, wall) for idx, wall in enumerate(walls) if wall.is_vertical(tol_deg=10.0)]
        x_clusters: List[List[Tuple[int, Segment]]] = []
        for idx, wall in vert_walls:
            x_mid = (wall.p1.x + wall.p2.x) / 2.0
            placed = False
            for cl in x_clusters:
                cl_x = sum((w.p1.x + w.p2.x) / 2.0 for _, w in cl) / len(cl)
                if abs(x_mid - cl_x) <= max(12.0, wall.thickness):
                    cl.append((idx, wall))
                    placed = True
                    break
            if not placed:
                x_clusters.append([(idx, wall)])

        for cl in x_clusters:
            # Sort by y_min
            cl.sort(key=lambda item: min(item[1].p1.y, item[1].p2.y))
            avg_x = sum((w.p1.x + w.p2.x) / 2.0 for _, w in cl) / len(cl)
            for i in range(len(cl) - 1):
                idx1, w1 = cl[i]
                idx2, w2 = cl[i + 1]
                y1_max = max(w1.p1.y, w1.p2.y)
                y2_min = min(w2.p1.y, w2.p2.y)
                gap_len = y2_min - y1_max
                if self.min_gap_px <= gap_len <= self.max_gap_px:
                    candidate_gaps.append((
                        idx1,
                        Point(avg_x, y1_max),
                        Point(avg_x, y2_min),
                        gap_len
                    ))

        # C. Internal gaps inside single long segments
        for w_idx, wall in enumerate(walls):
            if wall.length < self.min_gap_px * 2.0:
                continue
            internal_gaps = self._find_wall_gaps(wall, wall_mask)
            for g_start_t, g_end_t in internal_gaps:
                p_start = wall.point_at(g_start_t)
                p_end = wall.point_at(g_end_t)
                gap_len = p_start.distance_to(p_end)
                if self.min_gap_px <= gap_len <= self.max_gap_px:
                    candidate_gaps.append((w_idx, p_start, p_end, gap_len))

        # D. T-junction openings (door/window between endpoint and perpendicular wall)
        for v_idx, vw in vert_walls:
            vx = (vw.p1.x + vw.p2.x) / 2.0
            v_min_y = min(vw.p1.y, vw.p2.y)
            v_max_y = max(vw.p1.y, vw.p2.y)

            closer_up = any(
                abs((ow.p1.x + ow.p2.x) / 2.0 - vx) <= 15.0
                and max(ow.p1.y, ow.p2.y) < v_min_y
                and (v_min_y - max(ow.p1.y, ow.p2.y)) < 250.0
                for o_idx, ow in vert_walls if o_idx != v_idx
            )
            closer_down = any(
                abs((ow.p1.x + ow.p2.x) / 2.0 - vx) <= 15.0
                and min(ow.p1.y, ow.p2.y) > v_max_y
                and (min(ow.p1.y, ow.p2.y) - v_max_y) < 250.0
                for o_idx, ow in vert_walls if o_idx != v_idx
            )

            if not closer_up:
                for h_idx, hw in horiz_walls:
                    hy = (hw.p1.y + hw.p2.y) / 2.0
                    hx_min, hx_max = min(hw.p1.x, hw.p2.x), max(hw.p1.x, hw.p2.x)
                    if (hx_min - 25.0) <= vx <= (hx_max + 25.0) and hy < v_min_y:
                        dist = v_min_y - hy
                        if self.min_gap_px <= dist <= 180.0:
                            p_start, p_end = Point(vx, hy), Point(vx, v_min_y)
                            if self._has_opening_ink(p_start, p_end, thin_mask):
                                candidate_gaps.append((v_idx, p_start, p_end, dist))

            if not closer_down:
                for h_idx, hw in horiz_walls:
                    hy = (hw.p1.y + hw.p2.y) / 2.0
                    hx_min, hx_max = min(hw.p1.x, hw.p2.x), max(hw.p1.x, hw.p2.x)
                    if (hx_min - 25.0) <= vx <= (hx_max + 25.0) and hy > v_max_y:
                        dist = hy - v_max_y
                        if self.min_gap_px <= dist <= 180.0:
                            p_start, p_end = Point(vx, v_max_y), Point(vx, hy)
                            if self._has_opening_ink(p_start, p_end, thin_mask):
                                candidate_gaps.append((v_idx, p_start, p_end, dist))

        for h_idx, hw in horiz_walls:
            hy = (hw.p1.y + hw.p2.y) / 2.0
            h_min_x = min(hw.p1.x, hw.p2.x)
            h_max_x = max(hw.p1.x, hw.p2.x)

            closer_left = any(
                abs((ow.p1.y + ow.p2.y) / 2.0 - hy) <= 15.0
                and max(ow.p1.x, ow.p2.x) < h_min_x
                and (h_min_x - max(ow.p1.x, ow.p2.x)) < 250.0
                for o_idx, ow in horiz_walls if o_idx != h_idx
            )
            closer_right = any(
                abs((ow.p1.y + ow.p2.y) / 2.0 - hy) <= 15.0
                and min(ow.p1.x, ow.p2.x) > h_max_x
                and (min(ow.p1.x, ow.p2.x) - h_max_x) < 250.0
                for o_idx, ow in horiz_walls if o_idx != h_idx
            )

            if not closer_left:
                for v_idx, vw in vert_walls:
                    vx = (vw.p1.x + vw.p2.x) / 2.0
                    vy_min, vy_max = min(vw.p1.y, vw.p2.y), max(vw.p1.y, vw.p2.y)
                    if (vy_min - 25.0) <= hy <= (vy_max + 25.0) and vx < h_min_x:
                        dist = h_min_x - vx
                        if self.min_gap_px <= dist <= 180.0:
                            p_start, p_end = Point(vx, hy), Point(h_min_x, hy)
                            if self._has_opening_ink(p_start, p_end, thin_mask):
                                candidate_gaps.append((h_idx, p_start, p_end, dist))

            if not closer_right:
                for v_idx, vw in vert_walls:
                    vx = (vw.p1.x + vw.p2.x) / 2.0
                    vy_min, vy_max = min(vw.p1.y, vw.p2.y), max(vw.p1.y, vw.p2.y)
                    if (vy_min - 25.0) <= hy <= (vy_max + 25.0) and vx > h_max_x:
                        dist = vx - h_max_x
                        if self.min_gap_px <= dist <= 180.0:
                            p_start, p_end = Point(h_max_x, hy), Point(vx, hy)
                            if self._has_opening_ink(p_start, p_end, thin_mask):
                                candidate_gaps.append((h_idx, p_start, p_end, dist))

        # 3. Classify each candidate opening
        for w_idx, p_start, p_end, gap_len in candidate_gaps:
            is_ext = wall_exterior_map.get(w_idx, False)

            # Check if any detected door arc has hinge near this gap
            matched_arc = None
            for arc_center, arc_radius in detected_arcs:
                d_start = math.hypot(arc_center[0] - p_start.x, arc_center[1] - p_start.y)
                d_end = math.hypot(arc_center[0] - p_end.x, arc_center[1] - p_end.y)
                d_mid = math.hypot(arc_center[0] - (p_start.x + p_end.x) / 2, arc_center[1] - (p_start.y + p_end.y) / 2)
                min_dist = min(d_start, d_end, d_mid)

                if min_dist <= max(25.0, gap_len * 1.2):
                    # Arc radius should roughly match gap length
                    if abs(arc_radius - gap_len) < gap_len * 0.5:
                        matched_arc = (Point(arc_center[0], arc_center[1]), arc_radius)
                        break

            if matched_arc:
                hinge_pt, radius = matched_arc
                openings.append(
                    Opening(
                        id=f"door_{opening_idx:03d}",
                        kind="door",
                        wall_idx=w_idx,
                        p1=p_start,
                        p2=p_end,
                        width_px=gap_len,
                        hinge_px=hinge_pt,
                        arc_radius_px=radius,
                        is_exterior=is_ext,
                    )
                )
                opening_idx += 1
            else:
                # No swing arc detected:
                # Interior openings up to 95px are doors (standard residential doors ~700-1100mm).
                # Exterior openings can be doors (up to 95px with opening ink/thresholds) or windows (up to 180px).
                if not is_ext:
                    if 20.0 <= gap_len <= 95.0:
                        kind = "door"
                    else:
                        continue
                else:
                    if 20.0 <= gap_len <= 95.0 and self._has_opening_ink(p_start, p_end, thin_mask):
                        kind = "door"
                    elif 25.0 <= gap_len <= 180.0:
                        kind = "window"
                    else:
                        continue
                prefix = "window" if kind == "window" else "door"
                openings.append(
                    Opening(
                        id=f"{prefix}_{opening_idx:03d}",
                        kind=kind,
                        wall_idx=w_idx,
                        p1=p_start,
                        p2=p_end,
                        width_px=gap_len,
                        is_exterior=is_ext,
                    )
                )
                opening_idx += 1

        # Deduplicate openings close to each other
        unique_openings: List[Opening] = []
        for op in openings:
            duplicate = False
            for existing in unique_openings:
                if op.center_px.distance_to(existing.center_px) < 25.0:
                    duplicate = True
                    break
            if not duplicate:
                unique_openings.append(op)

        # Renumber sequentially
        final_openings: List[Opening] = []
        for idx, op in enumerate(unique_openings, start=1):
            final_openings.append(
                Opening(
                    id=f"{op.kind}_{idx:03d}",
                    kind=op.kind,
                    wall_idx=op.wall_idx,
                    p1=op.p1,
                    p2=op.p2,
                    width_px=op.width_px,
                    hinge_px=op.hinge_px,
                    arc_radius_px=op.arc_radius_px,
                    is_exterior=op.is_exterior,
                )
            )

        return final_openings

    def _has_opening_ink(self, p1: Point, p2: Point, thin_mask: np.ndarray, thresh: int = 100) -> bool:
        """Checks if thin linework, arcs, or opening threshold boxes exist along candidate gap."""
        import cv2
        h, w = thin_mask.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.line(mask, (int(round(p1.x)), int(round(p1.y))), (int(round(p2.x)), int(round(p2.y))), 255, 14)
        overlap = cv2.bitwise_and(thin_mask, mask)
        return bool(np.sum(overlap > 0) >= thresh)

    def _find_wall_gaps(self, wall: Segment, wall_mask: np.ndarray) -> List[Tuple[float, float]]:
        """Walks wall centerline and detects contiguous gaps in wall_mask."""
        h, w = wall_mask.shape[:2]
        length = wall.length
        step_px = 2.0
        num_steps = int(length / step_px)
        if num_steps < 10:
            return []

        samples: List[bool] = []
        for i in range(num_steps):
            t = i / float(num_steps)
            pt = wall.point_at(t)
            px = int(round(pt.x))
            py = int(round(pt.y))
            if 0 <= px < w and 0 <= py < h:
                samples.append(wall_mask[py, px] > 0)
            else:
                samples.append(False)

        gaps: List[Tuple[float, float]] = []
        in_gap = False
        gap_start_idx = 0
        margin = max(3, int(num_steps * 0.05))

        for i in range(margin, num_steps - margin):
            if not samples[i] and not in_gap:
                in_gap = True
                gap_start_idx = i
            elif samples[i] and in_gap:
                in_gap = False
                gap_end_idx = i
                t0 = gap_start_idx / float(num_steps)
                t1 = gap_end_idx / float(num_steps)
                gaps.append((t0, t1))

        return gaps

    def _find_door_arcs(self, thin_mask: np.ndarray) -> List[Tuple[Tuple[float, float], float]]:
        """
        Finds circular arcs in thin-line mask that correspond to door swings.
        Returns list of ((center_x, center_y), radius).
        """
        import cv2

        contours, _ = cv2.findContours(thin_mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        arcs: List[Tuple[Tuple[float, float], float]] = []

        for c in contours:
            x, y, bw, bh = cv2.boundingRect(c)
            max_d = max(bw, bh)
            min_d = min(bw, bh)
            if not (30 <= max_d <= 250):
                continue

            perim = cv2.arcLength(c, False)
            # Door swings are quarter-circles + radial line (aspect ratio >= 0.60)
            if (min_d / float(max_d)) >= 0.60 and perim >= (1.8 * max_d):
                # Bounding box width/height represents the door radius
                radius = float(max_d)
                cx = float(x + bw / 2.0)
                cy = float(y + bh / 2.0)
                arcs.append(((cx, cy), radius))

        return arcs
