"""Unit tests for Lane 1: CadExtractor."""

import json
from pathlib import Path
import pytest

from src.extraction import CadExtractor


def test_dxf_extraction_from_file():
    dxf_path = Path(__file__).parent.parent / "fixtures" / "sample_floorplan.dxf"
    assert dxf_path.exists(), "Sample DXF fixture must exist"

    extractor = CadExtractor(units="mm")
    data = extractor.extract_file(dxf_path)

    assert data["version"] == "1.0.0"
    assert data["units"] == "mm"
    assert len(data["elements"]) == 8

    # Verify classification of layers
    types = [e["type"] for e in data["elements"]]
    assert types.count("wall") == 4
    assert types.count("door") == 1
    assert types.count("window") == 1
    assert types.count("table") == 1
    assert types.count("chair") == 1


def test_dxf_schema_compliance():
    schema_path = Path(__file__).parent.parent / "schemas" / "lane1_input_schema.json"
    dxf_path = Path(__file__).parent.parent / "fixtures" / "sample_floorplan.dxf"

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    extractor = CadExtractor(units="mm")
    data = extractor.extract_file(dxf_path)

    for req in schema["required"]:
        assert req in data

    for elem in data["elements"]:
        assert "id" in elem
        assert "type" in elem
        assert elem["type"] in schema["properties"]["elements"]["items"]["properties"]["type"]["enum"]
        assert "position" in elem
        assert "scale" in elem
        assert "rotation" in elem


def test_layer_classifier_heuristics():
    extractor = CadExtractor()
    assert extractor.classify_layer("A-WALL-EXTR") == "wall"
    assert extractor.classify_layer("DOOR_SWING") == "door"
    assert extractor.classify_layer("GLAZING_WINDOW") == "window"
    assert extractor.classify_layer("I-FURN-DESK") == "table"
    assert extractor.classify_layer("SEATING") == "chair"
    assert extractor.classify_layer("UNKNOWN_LAYER") == "furniture"
