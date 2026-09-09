"""
Pure geometry structures and algorithms for 2D floor-plan vectorization.
Operates without external CV dependencies; highly unit-testable.
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass(frozen=True)
class Point:
    """A 2D point in continuous pixel or millimeter space."""
    x: float
    y: float

    def distance_to(self, other: Point) -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)

    def __add__(self, other: Point) -> Point:
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Point) -> Point:
        return Point(self.x - other.x, self.y - other.y)


@dataclass
class Segment:
    """A 2D directed line segment with an associated thickness."""
    p1: Point
    p2: Point
    thickness: float = 1.0

    @property
    def length(self) -> float:
        return self.p1.distance_to(self.p2)

    @property
    def dx(self) -> float:
        return self.p2.x - self.p1.x

    @property
    def dy(self) -> float:
        return self.p2.y - self.p1.y

    @property
    def midpoint(self) -> Point:
        return Point((self.p1.x + self.p2.x) / 2.0, (self.p1.y + self.p2.y) / 2.0)

    @property
    def angle_rad(self) -> float:
        """Returns angle in range [-pi, pi]."""
        return math.atan2(self.dy, self.dx)

    @property
    def angle_deg(self) -> float:
        """Returns orientation angle in [0, 180)."""
        deg = math.degrees(math.atan2(self.dy, self.dx)) % 180.0
        return deg

    def is_horizontal(self, tol_deg: float = 5.0) -> bool:
        ang = self.angle_deg
        return ang <= tol_deg or ang >= (180.0 - tol_deg)

    def is_vertical(self, tol_deg: float = 5.0) -> bool:
        ang = self.angle_deg
        return abs(ang - 90.0) <= tol_deg

    def point_at(self, t: float) -> Point:
        """Parametric point along segment: P(t) = P1 + t * (P2 - P1)."""
        return Point(self.p1.x + t * self.dx, self.p1.y + t * self.dy)

    def closest_point(self, pt: Point, clamp: bool = True) -> Point:
        """Project a point onto the segment."""
        l2 = self.dx * self.dx + self.dy * self.dy
        if l2 == 0:
            return self.p1
        t = ((pt.x - self.p1.x) * self.dx + (pt.y - self.p1.y) * self.dy) / l2
        if clamp:
            t = max(0.0, min(1.0, t))
        return self.point_at(t)

    def distance_to_point(self, pt: Point, clamp: bool = True) -> float:
        cp = self.closest_point(pt, clamp=clamp)
        return cp.distance_to(pt)


def union_intervals(intervals: List[Tuple[float, float]], gap_tol: float = 0.0) -> List[Tuple[float, float]]:
    """
    Merges overlapping or nearby 1D intervals [start, end].
    Assumes intervals are unordered and might have start > end.
    """
    if not intervals:
        return []

    normalized = [(min(s, e), max(s, e)) for s, e in intervals]
    normalized.sort(key=lambda x: x[0])

    merged = [normalized[0]]
    for cur_s, cur_e in normalized[1:]:
        prev_s, prev_e = merged[-1]
        if cur_s <= prev_e + gap_tol:
            # Overlapping or within gap_tol
            merged[-1] = (prev_s, max(prev_e, cur_e))
        else:
            merged.append((cur_s, cur_e))

    return merged


def dominant_angle(segments: List[Segment], bin_size_deg: float = 1.0) -> float:
    """
    Calculates dominant orientation angle modulo 90 degrees, weighted by segment length.
    Returns value in range [0, 90).
    """
    if not segments:
        return 0.0

    num_bins = int(90.0 / bin_size_deg)
    bins = [0.0] * num_bins

    for seg in segments:
        if seg.length < 5.0:
            continue
        # Fold angle into [0, 90)
        mod_deg = seg.angle_deg % 90.0
        bin_idx = int(mod_deg / bin_size_deg) % num_bins
        bins[bin_idx] += seg.length

    best_bin = max(range(num_bins), key=lambda i: bins[i])
    dominant = (best_bin + 0.5) * bin_size_deg
    # If very close to 0 or 90, snap to 0.0
    if dominant < 1.0 or dominant > 89.0:
        return 0.0
    return dominant


def merge_collinear(
    segments: List[Segment],
    dist_tol: float = 10.0,
    gap_tol: float = 20.0,
    angle_tol_deg: float = 5.0,
) -> List[Segment]:
    """
    Clusters segments that are roughly parallel and collinear,
    then merges overlapping intervals along their common projection axis.
    """
    if not segments:
        return []

    # Separate into horizontal, vertical, and other
    horizontals: List[Segment] = []
    verticals: List[Segment] = []
    others: List[Segment] = []

    for s in segments:
        if s.is_horizontal(angle_tol_deg):
            horizontals.append(s)
        elif s.is_vertical(angle_tol_deg):
            verticals.append(s)
        else:
            others.append(s)

    merged_out: List[Segment] = []

    # Merge horizontals: cluster by y-coordinate
    horizontals.sort(key=lambda s: (s.p1.y + s.p2.y) / 2.0)
    h_clusters: List[List[Segment]] = []
    for s in horizontals:
        y_mid = (s.p1.y + s.p2.y) / 2.0
        placed = False
        for cl in h_clusters:
            cl_y = sum((item.p1.y + item.p2.y) / 2.0 for item in cl) / len(cl)
            if abs(y_mid - cl_y) <= dist_tol:
                cl.append(s)
                placed = True
                break
        if not placed:
            h_clusters.append([s])

    for cl in h_clusters:
        avg_y = sum((item.p1.y + item.p2.y) / 2.0 for item in cl) / len(cl)
        avg_thick = sum(item.thickness for item in cl) / len(cl)
        intervals = [(s.p1.x, s.p2.x) for s in cl]
        for start_x, end_x in union_intervals(intervals, gap_tol=gap_tol):
            merged_out.append(Segment(Point(start_x, avg_y), Point(end_x, avg_y), thickness=avg_thick))

    # Merge verticals: cluster by x-coordinate
    verticals.sort(key=lambda s: (s.p1.x + s.p2.x) / 2.0)
    v_clusters: List[List[Segment]] = []
    for s in verticals:
        x_mid = (s.p1.x + s.p2.x) / 2.0
        placed = False
        for cl in v_clusters:
            cl_x = sum((item.p1.x + item.p2.x) / 2.0 for item in cl) / len(cl)
            if abs(x_mid - cl_x) <= dist_tol:
                cl.append(s)
                placed = True
                break
        if not placed:
            v_clusters.append([s])

    for cl in v_clusters:
        avg_x = sum((item.p1.x + item.p2.x) / 2.0 for item in cl) / len(cl)
        avg_thick = sum(item.thickness for item in cl) / len(cl)
        intervals = [(s.p1.y, s.p2.y) for s in cl]
        for start_y, end_y in union_intervals(intervals, gap_tol=gap_tol):
            merged_out.append(Segment(Point(avg_x, start_y), Point(avg_x, end_y), thickness=avg_thick))

    # Add remaining non-orthogonal segments
    merged_out.extend(others)
    return merged_out


def snap_junctions(segments: List[Segment], snap_dist: float = 15.0) -> List[Segment]:
    """
    Snaps endpoints that are close to each other (corner/L-junction)
    or close to an intersecting segment's interior (T-junction).
    """
    if not segments:
        return []

    # First pass: Snap near-meeting endpoints together (L-junctions)
    # Collect all endpoint references
    endpoints: List[Point] = []
    for s in segments:
        endpoints.append(s.p1)
        endpoints.append(s.p2)

    snapped_segments: List[Segment] = []
    for s in segments:
        p1 = s.p1
        p2 = s.p2

        # Check p1 against other segments
        new_p1 = p1
        for other in segments:
            if other is s:
                continue
            # Endpoints
            if p1.distance_to(other.p1) <= snap_dist:
                new_p1 = other.p1
                break
            elif p1.distance_to(other.p2) <= snap_dist:
                new_p1 = other.p2
                break
            # T-junction: interior of other
            cp = other.closest_point(p1, clamp=True)
            if p1.distance_to(cp) <= snap_dist:
                new_p1 = cp
                break

        # Check p2 against other segments
        new_p2 = p2
        for other in segments:
            if other is s:
                continue
            if p2.distance_to(other.p1) <= snap_dist:
                new_p2 = other.p1
                break
            elif p2.distance_to(other.p2) <= snap_dist:
                new_p2 = other.p2
                break
            cp = other.closest_point(p2, clamp=True)
            if p2.distance_to(cp) <= snap_dist:
                new_p2 = cp
                break

        # Ensure segments are oriented min-to-max for consistency
        if new_p1.x > new_p2.x or (abs(new_p1.x - new_p2.x) < 1e-4 and new_p1.y > new_p2.y):
            new_p1, new_p2 = new_p2, new_p1

        if new_p1.distance_to(new_p2) > 2.0:  # avoid zero-length
            snapped_segments.append(Segment(new_p1, new_p2, thickness=s.thickness))

    return snapped_segments
