"""Unit tests for Lane 3 3D scene generators and schema validation."""

import json
from pathlib import Path
import pytest

from src.generators.blender_generator import BlenderSceneBuilder


def test_blender_scene_builder_summary():
    fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_output.json"
    builder = BlenderSceneBuilder.from_file(str(fixture_path))

    summary = builder.get_summary()
    assert summary["element_count"] == 8
    assert summary["target_units"] == "m"
    assert "architectural" in summary["categories"]
    assert "furniture" in summary["categories"]


def test_lane3_output_schema_conformity():
    schema_path = Path(__file__).parent.parent / "schemas" / "lane3_output_schema.json"
    fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_output.json"

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Validate required top-level keys
    for req in schema["required"]:
        assert req in data

    # Validate each object in scene
    for obj in data["objects"]:
        assert "id" in obj
        assert "name" in obj
        assert "category" in obj
        assert "geometry" in obj
        assert "transform" in obj
        assert "material" in obj
        assert obj["geometry"]["primitive"] in ["box", "cylinder", "mesh", "plane"]


def test_generated_output_from_lane2_matches_lane3():
    generated_path = Path(__file__).parent.parent / "fixtures" / "generated_output.json"
    if generated_path.exists():
        builder = BlenderSceneBuilder.from_file(str(generated_path))
        summary = builder.get_summary()
        assert summary["element_count"] == 8
