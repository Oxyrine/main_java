"""Unified end-to-end pipeline orchestrating Lane 1, Lane 2, and Lane 3."""

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Union

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.extraction import CadExtractor
from src.parser import BlueprintParser
from src.exporter import SceneExporter
from src.models import BlueprintElement


@dataclass
class PipelineResult:
    """Encapsulates results and metrics of an end-to-end conversion."""
    source_file: str
    element_count: int
    element_types: Dict[str, int]
    scene_bounds: Dict[str, List[float]]
    scene_data: Dict[str, Any]
    output_json_path: Optional[Path] = None
    output_blend_path: Optional[Path] = None
    duration_ms: float = 0.0


class BlueprintTo3DPipeline:
    """
    Unified Orchestrator:
    Lane 1: CAD Blueprint Extraction (DXF/CSV/JSON)
    Lane 2: Object-Oriented Domain Model & Normalization
    Lane 3: 3D Scene Graph Generation & Export
    """

    def __init__(self, source_units: str = "mm", target_units: str = "m") -> None:
        self.source_units = source_units
        self.target_units = target_units
        self.extractor = CadExtractor(units=source_units)
        self.parser = BlueprintParser(default_units=source_units)
        self.exporter = SceneExporter(source_units=source_units, target_units=target_units)

    def process(
        self,
        input_path: Union[str, Path],
        output_json_path: Optional[Union[str, Path]] = None,
        output_blend_path: Optional[Union[str, Path]] = None,
    ) -> PipelineResult:
        """Executes the full pipeline from raw input to 3D scene output."""
        start_time = datetime.now()
        path = Path(input_path)
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {path}")

        # Stage 1 & Stage 2: Parse into typed OOP domain objects
        elements: List[BlueprintElement] = self.parser.parse_file(path)

        # Compute breakdown
        type_counts: Dict[str, int] = {}
        for elem in elements:
            type_counts[elem.element_type] = type_counts.get(elem.element_type, 0) + 1

        # Stage 3: Serialize to Lane 3 Scene Graph
        scene_dict = self.exporter.to_scene_dict(elements)
        scene_bounds = scene_dict["scene_metadata"].get("scene_bounds", {})

        # Save JSON if path provided
        json_out = None
        if output_json_path:
            json_out = self.exporter.export_to_file(elements, output_json_path)

        # Optional Blender batch execution if path requested
        blend_out = None
        if output_blend_path:
            from src.generators.blender_generator import BlenderSceneBuilder
            builder = BlenderSceneBuilder(scene_dict)
            builder.build_in_blender(str(output_blend_path))
            blend_out = Path(output_blend_path)

        elapsed = (datetime.now() - start_time).total_seconds() * 1000.0

        return PipelineResult(
            source_file=path.name,
            element_count=len(elements),
            element_types=type_counts,
            scene_bounds=scene_bounds,
            scene_data=scene_dict,
            output_json_path=json_out,
            output_blend_path=blend_out,
            duration_ms=round(elapsed, 2),
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Unified 2D Blueprint to 3D Scene Pipeline (Lanes 1, 2, and 3)"
    )
    parser.add_argument(
        "-i", "--input",
        type=str,
        required=True,
        help="Input blueprint file (.dxf, .csv, or .json)",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="fixtures/generated_output.json",
        help="Path for exported 3D scene JSON (default: fixtures/generated_output.json)",
    )
    parser.add_argument(
        "--blend",
        type=str,
        default=None,
        help="Optional path to output Blender .blend file (requires Blender bpy)",
    )

    args = parser.parse_args()

    pipeline = BlueprintTo3DPipeline()
    print("=" * 65)
    print("  === 2D Blueprint to 3D Model Conversion Pipeline ===")
    print("=" * 65)
    print(f"Processing input : {args.input}")

    try:
        res = pipeline.process(args.input, args.output, args.blend)
    except Exception as e:
        print(f"Pipeline error: {e}", file=sys.stderr)
        return 1

    print(f"\n[OK] Stage 1 & 2: Parsed {res.element_count} OOP objects in {res.duration_ms} ms.")
    print("    Element Classification:")
    for k, v in res.element_types.items():
        print(f"      - {k.capitalize():<12}: {v}")

    print(f"\n[OK] Stage 3: Generated 3D Scene Graph")
    print(f"    Scene Bounds (m): Min {res.scene_bounds.get('min')} -> Max {res.scene_bounds.get('max')}")
    print(f"    Saved Scene JSON : {res.output_json_path}")
    if res.output_blend_path:
        print(f"    Saved Blend File : {res.output_blend_path}")
    print("=" * 65)
    return 0


if __name__ == "__main__":
    sys.exit(main())
