"""Unit tests for the BlueprintParser."""

from pathlib import Path
import pytest

from src.models import Chair, Door, Table, Vector3D, Wall, Window
from src.parser import BlueprintParser


def test_parse_json_fixture():
    fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_input.json"
    parser = BlueprintParser(default_units="mm")
    elements = parser.parse_file(fixture_path)

    assert len(elements) == 8

    # Verify types parsed polymorphically
    types = [e.element_type for e in elements]
    assert types.count("wall") == 4
    assert types.count("door") == 1
    assert types.count("window") == 1
    assert types.count("table") == 1
    assert types.count("chair") == 1

    # Check that wall_001 is an instance of Wall
    wall_1 = next(e for e in elements if e.element_id == "wall_001")
    assert isinstance(wall_1, Wall)
    assert wall_1.scale.x == 5000.0


def test_parse_csv_fixture():
    fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_input.csv"
    parser = BlueprintParser(default_units="mm")
    elements = parser.parse_file(fixture_path)

    assert len(elements) == 8
    door = next(e for e in elements if e.element_id == "door_001")
    assert isinstance(door, Door)
    assert door.scale.x == 900.0


def test_heuristic_type_inference():
    parser = BlueprintParser()

    # Long thin element -> Wall
    elem_wall = parser.create_element(
        element_id="test_1",
        element_type=None,
        position=Vector3D(0, 0, 0),
        scale=Vector3D(4500, 250, 2800),
    )
    assert isinstance(elem_wall, Wall)

    # Standard door dimensions -> Door
    elem_door = parser.create_element(
        element_id="test_2",
        element_type="",
        position=Vector3D(0, 0, 0),
        scale=Vector3D(900, 200, 2100),
    )
    assert isinstance(elem_door, Door)

    # Small square footprint -> Chair
    elem_chair = parser.create_element(
        element_id="test_3",
        element_type=None,
        position=Vector3D(0, 0, 0),
        scale=Vector3D(450, 450, 850),
    )
    assert isinstance(elem_chair, Chair)

    # Medium rectangular footprint -> Table
    elem_table = parser.create_element(
        element_id="test_4",
        element_type=None,
        position=Vector3D(0, 0, 0),
        scale=Vector3D(1400, 800, 750),
    )
    assert isinstance(elem_table, Table)


def test_parse_legacy_csv_multileaders():
    """Test parsing the project's original untyped CSV using heuristic fallback."""
    legacy_csv = Path(__file__).parent.parent / "Data Extraction and Multileaders Sample Coordinates.csv"
    if legacy_csv.exists():
        parser = BlueprintParser()
        elements = parser.parse_file(legacy_csv)
        assert len(elements) > 0
        # Check that elements are classified without crashing
        assert all(isinstance(e, Wall) or hasattr(e, "element_type") for e in elements)
