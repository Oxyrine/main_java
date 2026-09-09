"""
End-to-end integration tests for the OpenCV-based floor-plan computer vision pipeline.
Guarded with pytest.importorskip('cv2') to ensure graceful test execution.
"""

from pathlib import Path
import pytest

# Guard all tests in this file
cv2 = pytest.importorskip("cv2")

from src.vision.config import VisionConfig
from src.vision.floorplan_vision import FloorPlanVisionExtractor
from src.extraction.cad_extractor import CadExtractor
from src.parser.input_parser import BlueprintParser
from src.exporter.scene_exporter import SceneExporter
from tools.make_sample_floorplan_png import create_sample_floorplan_png


@pytest.fixture(scope="module")
def sample_png(tmp_path_factory) -> Path:
    """Generates synthetic floor plan PNG once for the test module."""
    tmp_dir = tmp_path_factory.mktemp("vision_fixtures")
    png_path = tmp_dir / "test_floorplan.png"
    create_sample_floorplan_png(png_path)
    return png_path


def test_floorplan_vision_extractor_end_to_end(sample_png: Path):
    """Verifies that the CV pipeline accurately reconstructs rooms, walls, and scale."""
    cfg = VisionConfig(enable_ocr=False)
    extractor = FloorPlanVisionExtractor(config=cfg)
    result = extractor.extract(sample_png)

    # 1. Envelope compliance
    assert result["version"] == "1.0.0"
    assert result["units"] == "mm"
    assert "metadata" in result
    meta = result["metadata"]
    assert meta["entity_count"] > 0
    assert "scale_inference" in meta

    # 2. Scale inference: Door arcs were drawn with radius=85px, default door is 850mm -> 10mm/px
    scale_info = meta["scale_inference"]
    mm_per_px = scale_info["mm_per_px"]
    assert 7.0 <= mm_per_px <= 13.0, f"Recovered scale {mm_per_px} mm/px outside expected range (~10 mm/px)"

    # 3. Element classification
    elements = result["elements"]
    walls = [e for e in elements if e["type"] == "wall"]
    doors = [e for e in elements if e["type"] == "door"]
    windows = [e for e in elements if e["type"] == "window"]
    floors = [e for e in elements if e["type"] == "floor"]

    # Exactly 3 rooms drawn in synthetic plan
    assert len(floors) == 3, f"Expected 3 floor slabs, found {len(floors)}"
    assert len(walls) >= 4, f"Expected at least 4 walls, found {len(walls)}"
    assert len(doors) >= 1, f"Expected at least 1 door, found {len(doors)}"
    assert len(windows) >= 1, f"Expected at least 1 window, found {len(windows)}"

    # 4. Check that exterior walls are properly classified
    ext_walls = [w for w in walls if w["properties"].get("exterior") is True]
    assert len(ext_walls) >= 3, "Expected exterior walls to be identified"


def test_cad_extractor_delegates_to_vision(sample_png: Path):
    """Asserts that CadExtractor.extract_image() delegates to the vision pipeline."""
    extractor = CadExtractor(units="mm")
    data = extractor.extract_file(sample_png)

    assert data["version"] == "1.0.0"
    assert any(e["type"] == "floor" for e in data["elements"])


def test_end_to_end_oop_conversion_and_export(sample_png: Path):
    """Tests full pipeline from PNG -> OOP Objects -> Lane 3 3D Scene JSON."""
    parser = BlueprintParser(default_units="mm")
    elements = parser.parse_file(sample_png)

    assert len(elements) > 0
    types = {e.element_type for e in elements}
    assert "wall" in types
    assert "floor" in types

    # Export to Lane 3 Scene Graph
    exporter = SceneExporter(source_units="mm", target_units="m")
    scene_data = exporter.to_scene_dict(elements)

    assert scene_data["format_version"] == "1.0.0"
    objects = scene_data["objects"]
    assert len(objects) == len(elements)

    # Floor objects should have category 'architectural'
    floor_objs = [o for o in objects if o["type"] == "floor"]
    assert len(floor_objs) == 3
    for f in floor_objs:
        assert f["category"] == "architectural"
        assert f["geometry"]["primitive"] == "box"


def test_vision_grey_wall_floorplan(tmp_path: Path):
    """Verifies vision pipeline detects grey walls, door thresholds, and multi-colored rooms."""
    import numpy as np
    w, h = 600, 600
    img = np.full((h, w, 3), (230, 242, 255), dtype=np.uint8)  # Warm peach fill

    # Wet area (blue/lavender) in top-left
    img[20:250, 20:250] = (255, 190, 190)

    # Exterior grey walls (V ~ 178, thickness 14px)
    cv2.rectangle(img, (20, 20), (580, 580), (178, 178, 178), 14)
    # Interior dividing walls
    cv2.line(img, (250, 20), (250, 580), (178, 178, 178), 14)
    cv2.line(img, (20, 250), (580, 250), (178, 178, 178), 14)

    # Door openings: replace wall with black threshold box (80px wide)
    img[243:257, 100:180] = (0, 0, 0)
    img[243:257, 350:430] = (0, 0, 0)

    # Window openings: replace exterior wall with black window frame (140px wide)
    img[13:27, 330:470] = (0, 0, 0)
    img[573:587, 100:240] = (0, 0, 0)

    plan_path = tmp_path / "grey_plan.png"
    cv2.imwrite(str(plan_path), img)

    extractor = FloorPlanVisionExtractor(VisionConfig(enable_ocr=False))
    result = extractor.extract(plan_path)

    types = {e["type"] for e in result["elements"]}
    assert "wall" in types
    assert "floor" in types
    assert "door" in types
    assert "window" in types

    floors = [e for e in result["elements"] if e["type"] == "floor"]
    assert len(floors) == 4, f"Expected 4 rooms, got {len(floors)}"

