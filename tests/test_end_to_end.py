"""End-to-end integration tests connecting Lanes 1, 2, and 3."""

from pathlib import Path
import pytest

from src.pipeline import BlueprintTo3DPipeline


def test_pipeline_dxf_end_to_end(tmp_path: Path):
    dxf_path = Path(__file__).parent.parent / "fixtures" / "sample_floorplan.dxf"
    out_json = tmp_path / "e2e_scene.json"

    pipeline = BlueprintTo3DPipeline(source_units="mm", target_units="m")
    result = pipeline.process(dxf_path, output_json_path=out_json)

    assert result.element_count == 8
    assert result.element_types["wall"] == 4
    assert result.element_types["door"] == 1
    assert result.element_types["window"] == 1
    assert result.element_types["table"] == 1
    assert result.element_types["chair"] == 1

    assert out_json.exists()
    assert result.scene_data["format_version"] == "1.0.0"
    assert len(result.scene_data["objects"]) == 8


def test_pipeline_csv_end_to_end():
    csv_path = Path(__file__).parent.parent / "fixtures" / "sample_input.csv"
    pipeline = BlueprintTo3DPipeline()
    result = pipeline.process(csv_path)

    assert result.element_count == 8
    assert "wall" in result.element_types
    assert result.duration_ms >= 0.0


def test_pipeline_legacy_cad_end_to_end():
    legacy_csv = Path(__file__).parent.parent / "Data Extraction and Multileaders Sample Coordinates.csv"
    if legacy_csv.exists():
        pipeline = BlueprintTo3DPipeline()
        result = pipeline.process(legacy_csv)
        assert result.element_count == 222
        assert len(result.scene_data["objects"]) == 222
