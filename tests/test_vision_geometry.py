"""
Unit tests for pure geometry functions in src/vision/geometry.py.
No cv2 dependencies; runs fast and deterministically.
"""

import math
import pytest
from src.vision.geometry import (
    Point,
    Segment,
    union_intervals,
    dominant_angle,
    merge_collinear,
    snap_junctions,
)


def test_point_operations():
    p1 = Point(10.0, 20.0)
    p2 = Point(13.0, 24.0)
    assert p1.distance_to(p2) == 5.0
    assert p1.to_tuple() == (10.0, 20.0)
    diff = p2 - p1
    assert diff.x == 3.0 and diff.y == 4.0
    added = p1 + p2
    assert added.x == 23.0 and added.y == 44.0


def test_segment_properties():
    s = Segment(Point(0.0, 0.0), Point(10.0, 0.0), thickness=2.0)
    assert s.length == 10.0
    assert s.is_horizontal()
    assert not s.is_vertical()
    assert s.midpoint == Point(5.0, 0.0)
    assert s.angle_deg == 0.0

    s_vert = Segment(Point(5.0, 0.0), Point(5.0, 15.0))
    assert s_vert.length == 15.0
    assert s_vert.is_vertical()
    assert not s_vert.is_horizontal()
    assert s_vert.angle_deg == 90.0


def test_union_intervals():
    intervals = [(0, 10), (5, 15), (20, 30), (28, 35)]
    merged = union_intervals(intervals)
    assert merged == [(0, 15), (20, 35)]

    # With gap tolerance
    intervals2 = [(0, 10), (12, 20)]
    merged_gap = union_intervals(intervals2, gap_tol=3.0)
    assert merged_gap == [(0, 20)]

    assert union_intervals([]) == []


def test_dominant_angle():
    # Mostly horizontal segments
    segs = [
        Segment(Point(0, 0), Point(100, 0)),
        Segment(Point(0, 50), Point(80, 0.5)),  # slight slope < 1 deg
        Segment(Point(0, 0), Point(0, 50)),     # 50 length vertical
    ]
    angle = dominant_angle(segs)
    assert angle == 0.0


def test_merge_collinear_horizontals():
    segs = [
        Segment(Point(0, 100), Point(50, 100), thickness=2.0),
        Segment(Point(40, 101), Point(120, 101), thickness=2.0),  # overlapping horizontally, within 1px dist
        Segment(Point(150, 100), Point(200, 100), thickness=2.0), # disjoint
    ]
    merged = merge_collinear(segs, dist_tol=5.0, gap_tol=10.0)
    assert len(merged) == 2
    # First merged span should be 0 to 120
    m1 = [m for m in merged if m.p1.x == 0][0]
    assert m1.p2.x == 120.0
    assert abs(m1.p1.y - 100.5) < 0.6


def test_snap_junctions():
    # L-junction: Horizontal ending at (98, 100), Vertical starting at (100, 95)
    s_h = Segment(Point(0, 100), Point(98, 100), thickness=2.0)
    s_v = Segment(Point(100, 95), Point(100, 200), thickness=2.0)

    snapped = snap_junctions([s_h, s_v], snap_dist=10.0)
    assert len(snapped) == 2
    # Endpoints should meet
    assert any(s.p2 == Point(100, 95) or s.p1 == Point(98, 100) for s in snapped)
