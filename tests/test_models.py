"""Unit tests for core OOP models."""

import pytest
from src.models import (
    BlueprintElement,
    Chair,
    Door,
    GenericFurniture,
    Table,
    Vector3D,
    Wall,
    Window,
)


def test_vector3d_operations():
    v1 = Vector3D(10.0, 20.0, 30.0)
    scaled = v1.scaled_by(0.1)
    assert scaled.x == pytest.approx(1.0)
    assert scaled.y == pytest.approx(2.0)
    assert scaled.z == pytest.approx(3.0)

    v2 = Vector3D(5.0, 5.0, 5.0)
    added = v1.add(v2)
    assert added.x == 15.0
    assert added.y == 25.0
    assert added.z == 35.0

    assert v1.to_dict() == {"x": 10.0, "y": 20.0, "z": 30.0}
    assert v1.to_list() == [10.0, 20.0, 30.0]


def test_wall_model():
    wall = Wall(
        element_id="w_01",
        position=Vector3D(0.0, 0.0, 0.0),
        scale=Vector3D(4000.0, 200.0, 2800.0),
        properties={"exterior": True, "material": "brick"},
    )
    assert wall.element_type == "wall"
    assert wall.category == "architectural"
    assert wall.is_exterior is True
    assert wall.get_default_material().name == "ExteriorWallMaterial"

    # Test center calculation with mm to m scaling
    center = wall.get_center_in_world(unit_scale=0.001)
    assert center.x == pytest.approx(2.0)
    assert center.y == pytest.approx(0.1)
    assert center.z == pytest.approx(1.4)

    # Test bounding box in mm
    b_min, b_max = wall.get_bounding_box()
    assert b_min.x == 0.0
    assert b_max.x == 4000.0


def test_door_model():
    door = Door(
        element_id="d_01",
        position=Vector3D(1000.0, 0.0, 0.0),
        scale=Vector3D(900.0, 150.0, 2100.0),
        properties={"swing_direction": "outward", "open_angle": 45.0},
    )
    assert door.element_type == "door"
    assert door.category == "architectural"
    assert door.swing_direction == "outward"
    assert door.open_angle == 45.0
    assert door.get_default_material().name == "WoodDoorMaterial"


def test_window_model():
    window = Window(
        element_id="win_01",
        position=Vector3D(2000.0, 0.0, 1000.0),
        scale=Vector3D(1200.0, 200.0, 1200.0),
        properties={"glazing": "triple", "sill_height": 1000.0},
    )
    assert window.element_type == "window"
    assert window.category == "architectural"
    assert window.glazing == "triple"
    assert window.get_default_material().name == "GlassMaterial"
    # Glass material has low roughness and semi-transparent alpha
    mat = window.get_default_material()
    assert mat.roughness == 0.1
    assert mat.color[3] < 1.0


def test_furniture_models():
    table = Table(
        element_id="t_01",
        position=Vector3D(500.0, 500.0, 0.0),
        scale=Vector3D(1500.0, 800.0, 750.0),
    )
    assert table.element_type == "table"
    assert table.category == "furniture"

    chair = Chair(
        element_id="c_01",
        position=Vector3D(500.0, 600.0, 0.0),
        scale=Vector3D(500.0, 500.0, 850.0),
        properties={"swivel": True},
    )
    assert chair.element_type == "chair"
    assert chair.category == "furniture"
    assert chair.is_swivel is True

    generic = GenericFurniture(
        element_id="g_01",
        type_name="bookshelf",
        position=Vector3D(0.0, 0.0, 0.0),
        scale=Vector3D(800.0, 300.0, 2000.0),
    )
    assert generic.element_type == "bookshelf"
    assert generic.category == "furniture"


def test_to_3d_object_serialization():
    wall = Wall(
        element_id="w_test",
        position=Vector3D(1000.0, 2000.0, 0.0),
        scale=Vector3D(3000.0, 200.0, 2500.0),
    )
    obj = wall.to_3d_object(unit_scale=0.001)

    assert obj["id"] == "w_test"
    assert obj["type"] == "wall"
    assert obj["category"] == "architectural"
    assert obj["geometry"]["primitive"] == "box"
    assert obj["geometry"]["dimensions"]["width"] == pytest.approx(3.0)
    assert obj["geometry"]["dimensions"]["depth"] == pytest.approx(0.2)
    assert obj["geometry"]["dimensions"]["height"] == pytest.approx(2.5)
    # Center: (1000 + 1500) * 0.001 = 2.5
    assert obj["transform"]["translation"]["x"] == pytest.approx(2.5)
    assert "material" in obj
