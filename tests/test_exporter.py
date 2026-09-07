"""Unit tests for SceneExporter."""

import json
from pathlib import Path
import pytest

from src.exporter import SceneExporter
from src.models import Vector3D, Wall, Door


def test_exporter_unit_conversion():
    wall = Wall(
        element_id="w_01",
        position=Vector3D(0.0, 0.0, 0.0),
        scale=Vector3D(3000.0, 200.0, 2800.0),
    )
    door = Door(
        element_id="d_01",
        position=Vector3D(1000.0, 0.0, 0.0),
        scale=Vector3D(900.0, 200.0, 2100.0),
    )

    # Convert mm to m
    exporter = SceneExporter(source_units="mm", target_units="m")
    scene = exporter.to_scene_dict([wall, door])

    assert scene["format_version"] == "1.0.0"
    assert scene["scene_metadata"]["target_units"] == "m"
    assert scene["scene_metadata"]["element_count"] == 2

    # Dimensions in meters
    obj_wall = scene["objects"][0]
    assert obj_wall["geometry"]["dimensions"]["width"] == pytest.approx(3.0)
    assert obj_wall["geometry"]["dimensions"]["depth"] == pytest.approx(0.2)
    assert obj_wall["geometry"]["dimensions"]["height"] == pytest.approx(2.8)


def test_exporter_file_writing(tmp_path: Path):
    wall = Wall(
        element_id="w_01",
        position=Vector3D(0.0, 0.0, 0.0),
        scale=Vector3D(1000.0, 100.0, 2000.0),
    )
    exporter = SceneExporter()
    out_file = tmp_path / "test_scene.json"
    exporter.export_to_file([wall], out_file)

    assert out_file.exists()
    with open(out_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["scene_metadata"]["element_count"] == 1
    assert data["objects"][0]["id"] == "w_01"
