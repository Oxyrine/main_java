"""
Wall detection stage: HSV thresholding, distance-transform thickness filtering,
and vectorization into snapped wall segments.
"""

from __future__ import annotations
import math
from typing import List, Tuple, Optional
import numpy as np

from src.vision.geometry import Point, Segment, dominant_angle, merge_collinear, snap_junctions
from src.vision.preprocess import PreparedImage


class WallDetector:
    """Detects and vectorizes solid architectural walls from prepared raster images."""

    def __init__(self, min_length_px: float = 25.0):
        self.min_length_px = min_length_px

    def detect(
        self,
        prepared: PreparedImage,
        free_angle: bool = False
    ) -> Tuple[List[Segment], np.ndarray, np.ndarray, float]:
        """
        Executes wall detection pipeline.
        Returns:
            (wall_segments, wall_mask, thin_mask, estimated_thickness_px)
        """
        import cv2

        # 1. Analyze chromatic and value distribution
        hsv = cv2.cvtColor(prepared.bgr, cv2.COLOR_BGR2HSV)
        s = hsv[:, :, 1]
        v = hsv[:, :, 2]

        achromatic = (s < 45)
        v_achro = v[achromatic]

        # Check for mid-tone grey wall fill peak (V between 80 and 220)
        # Real architectural walls occupy between 2% and 22% of total drawing area.
        # If mid-grey exceeds 22%, it represents shaded room floors (e.g. SweetHome3D), not walls.
        total_px = prepared.working_w * prepared.working_h
        mid_grey = v_achro[(v_achro >= 80) & (v_achro <= 220)]
        has_mid_grey_wall = False
        v_peak = 0.0

        if (total_px * 0.02) < len(mid_grey) < (total_px * 0.22):
            hist, bin_edges = np.histogram(mid_grey, bins=28, range=(80, 220))
            peak_idx = int(np.argmax(hist))
            if hist[peak_idx] > (total_px * 0.015):
                v_peak = float((bin_edges[peak_idx] + bin_edges[peak_idx + 1]) / 2.0)
                has_mid_grey_wall = True

        if has_mid_grey_wall:
            # Plan uses a solid mid-grey wall fill (e.g. V ~ 178)
            # Wall candidates are the solid grey fill pixels!
            wall_ink = achromatic & (np.abs(v.astype(float) - v_peak) <= 25)
            # Thin mask holds the black linework, door arcs, text, and threshold boxes
            thin_ink = achromatic & (v < max(60, int(v_peak - 40)))
            ink_mask = wall_ink.astype(np.uint8) * 255
            thin_base = thin_ink.astype(np.uint8) * 255
        else:
            # Check if drawing has shaded room floors (> 22% mid-grey)
            if len(mid_grey) >= (total_px * 0.22):
                # Walls are the dark boundaries and partition strokes around the floors
                ink_mask = ((v < 80) | ((s > 15) & (v < 130))).astype(np.uint8) * 255
            else:
                # Monochrome / dark-ink plan: walls are dark linework
                ink_mask = ((s < 70) & (v < 215)).astype(np.uint8) * 255
                if np.mean(v) < 100:
                    ink_mask = ((s < 70) & (v > 100)).astype(np.uint8) * 255
            thin_base = ink_mask

        # Filter out tiny speckles/hatching components from ink_mask.
        # Real architectural walls have substantial area and span, whereas paving hatching,
        # stipples, dimension text, and legend symbols are small isolated clusters.
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(ink_mask)
        if num_labels > 40:
            filtered_ink = np.zeros_like(ink_mask)
            for i in range(1, num_labels):
                area = stats[i, cv2.CC_STAT_AREA]
                w_box = stats[i, cv2.CC_STAT_WIDTH]
                h_box = stats[i, cv2.CC_STAT_HEIGHT]
                if area >= 60 and max(w_box, h_box) >= 20:
                    filtered_ink[labels == i] = 255
            ink_mask = filtered_ink

        # For drawings with double-line walls (e.g. vintage architectural scans),
        # parallel thin lines are separated by a small gap (3-8px).
        # Morphological close bridges the hollow wall gap into solid wall volume.
        k_bridge = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        ink_closed = cv2.morphologyEx(ink_mask, cv2.MORPH_CLOSE, k_bridge)

        # 2. Distance Transform to isolate thick walls from thin linework/text
        dist = cv2.distanceTransform(ink_closed, cv2.DIST_L2, 5)

        # Estimate wall thickness from medial-axis ridge values
        r_est = self._estimate_ridge_radius(dist)
        t_est = max(6.0, r_est * 2.0)

        # Threshold distance transform: adaptive for thin/double-line vs thick poche walls
        thresh_r = max(2.0, r_est * 0.35) if dist.max() > 6.0 else 1.2
        wall_mask = (dist >= thresh_r).astype(np.uint8) * 255

        # Morphological close to bridge tiny gaps and smooth wall cores
        k_size = max(3, int(round(r_est * 0.5)))
        if k_size % 2 == 0:
            k_size += 1
        k = cv2.getStructuringElement(cv2.MORPH_RECT, (k_size, k_size))
        wall_mask = cv2.morphologyEx(wall_mask, cv2.MORPH_CLOSE, k)

        # Thin mask: linework, text, and door arcs with wall contact points cleanly disconnected
        k_dil = max(7, int(round(t_est * 0.75)))
        if k_dil % 2 == 0:
            k_dil += 1
        dilated_wall = cv2.dilate(wall_mask, cv2.getStructuringElement(cv2.MORPH_RECT, (k_dil, k_dil)))
        thin_mask = cv2.bitwise_and(thin_base, cv2.bitwise_not(dilated_wall))

        # 3. Vectorize Wall Mask
        edges = cv2.Canny(wall_mask, 50, 150)
        hough_thresh = max(30, int(t_est * 1.5))
        min_line_len = max(int(self.min_length_px), int(t_est * 1.5))
        max_line_gap = max(12, int(t_est * 1.2))

        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180,
            threshold=hough_thresh,
            minLineLength=min_line_len,
            maxLineGap=max_line_gap
        )

        raw_segments: List[Segment] = []
        if lines is not None:
            for l in lines:
                x1, y1, x2, y2 = l.ravel()[:4]
                seg = Segment(Point(float(x1), float(y1)), Point(float(x2), float(y2)), thickness=t_est)
                if seg.length >= self.min_length_px:
                    raw_segments.append(seg)

        # 4. Snap to dominant Manhattan orientation
        dom_deg = dominant_angle(raw_segments)
        snapped_segments: List[Segment] = []
        for seg in raw_segments:
            if free_angle:
                snapped_segments.append(seg)
            else:
                s_snapped = self._snap_to_manhattan(seg, dom_deg, tol_deg=7.5)
                snapped_segments.append(s_snapped)

        # 5. Merge collinear overlapping lines and snap junctions
        # Keep gap_tol under 25px so door openings (60-90px) are never bridged
        merged = merge_collinear(snapped_segments, dist_tol=t_est * 0.9, gap_tol=min(25.0, t_est * 1.5))
        snapped_walls = snap_junctions(merged, snap_dist=min(20.0, t_est * 1.2))

        # 6. Sample local thickness along centerline of each wall
        final_walls: List[Segment] = []
        h, w = dist.shape[:2]
        for wall in snapped_walls:
            samples = []
            num_samples = max(3, int(wall.length / 10.0))
            for i in range(num_samples):
                t_param = (i + 0.5) / num_samples
                pt = wall.point_at(t_param)
                px = int(round(pt.x))
                py = int(round(pt.y))
                if 0 <= px < w and 0 <= py < h:
                    val = dist[py, px]
                    if val > 1.0:
                        samples.append(val)

            sampled_thick = (float(np.median(samples)) * 2.0) if len(samples) >= 2 else t_est
            sampled_thick = max(6.0, sampled_thick)
            final_walls.append(Segment(wall.p1, wall.p2, thickness=sampled_thick))

        return final_walls, wall_mask, thin_mask, t_est

    def _estimate_ridge_radius(self, dist: np.ndarray) -> float:
        """Finds the mode of local distance-transform maxima (ridge values)."""
        import cv2

        # Morphological dilation to find local 3x3 maxima
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        dilated = cv2.dilate(dist, kernel)

        # Ridge pixels are local maxima with dist >= 2.5
        ridge_mask = (dist == dilated) & (dist >= 2.5)
        ridge_values = dist[ridge_mask]

        if len(ridge_values) < 20:
            return 8.0  # Default 8px radius (~16px wall)

        # Histogram between 2.5 and 40 with 0.5 step
        bins = np.arange(2.5, 40.0, 0.5)
        hist, bin_edges = np.histogram(ridge_values, bins=bins)
        peak_idx = int(np.argmax(hist))
        mode_val = float((bin_edges[peak_idx] + bin_edges[peak_idx + 1]) / 2.0)
        return mode_val

    def _snap_to_manhattan(self, seg: Segment, dominant_angle_deg: float, tol_deg: float = 7.5) -> Segment:
        """Snaps segment to horizontal or vertical if close to Manhattan axes."""
        ang = seg.angle_deg
        # Check horizontal (close to 0 or 180)
        if ang <= tol_deg or ang >= (180.0 - tol_deg):
            avg_y = (seg.p1.y + seg.p2.y) / 2.0
            return Segment(Point(seg.p1.x, avg_y), Point(seg.p2.x, avg_y), thickness=seg.thickness)
        # Check vertical (close to 90)
        if abs(ang - 90.0) <= tol_deg:
            avg_x = (seg.p1.x + seg.p2.x) / 2.0
            return Segment(Point(avg_x, seg.p1.y), Point(avg_x, seg.p2.y), thickness=seg.thickness)
        return seg
