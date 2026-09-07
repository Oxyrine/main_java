"""Command-line interface for running the Lane 2 Blueprint to 3D pipeline."""

import argparse
from collections import Counter
from pathlib import Path
import sys

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.exporter import SceneExporter
from src.parser import BlueprintParser


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lane 2: Convert CAD 2D Blueprint tabular/JSON data into typed 3D scene representation."
    )
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        default="fixtures/sample_input.json",
        help="Path to input blueprint file (JSON or CSV). Defaults to fixtures/sample_input.json",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="fixtures/generated_output.json",
        help="Path for exported Lane 3 scene JSON. Defaults to fixtures/generated_output.json",
    )
    parser.add_argument(
        "--source-units",
        type=str,
        default="mm",
        choices=["mm", "cm", "m", "inch", "foot"],
        help="Units used in the input blueprint data (default: mm)",
    )
    parser.add_argument(
        "--target-units",
        type=str,
        default="m",
        choices=["m", "mm", "cm"],
        help="Target units for 3D generation (default: m)",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    print("=" * 60)
    print("  Lane 2: OOP Blueprint to 3D Model Converter")
    print("=" * 60)
    print(f"Reading input from : {input_path}")

    if not input_path.exists():
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        return 1

    # Step 1: Parse input data into OOP objects
    blueprint_parser = BlueprintParser(default_units=args.source_units)
    try:
        elements = blueprint_parser.parse_file(input_path)
    except Exception as e:
        print(f"Error while parsing input file: {e}", file=sys.stderr)
        return 1

    print(f"Successfully parsed: {len(elements)} elements.")

    # Breakdown by element type
    counts = Counter(elem.element_type for elem in elements)
    print("\nElement Breakdown:")
    for elem_type, count in counts.items():
        print(f"  - {elem_type.capitalize():<12}: {count}")

    # Step 2: Export to Lane 3 scene graph JSON
    exporter = SceneExporter(source_units=args.source_units, target_units=args.target_units)
    out_file = exporter.export_to_file(elements, output_path)

    bounds = exporter.calculate_scene_bounds(elements)
    print("\nScene Bounding Box (in meters):")
    print(f"  Min: {bounds['min']}")
    print(f"  Max: {bounds['max']}")

    print(f"\nExported 3D Scene JSON saved to: {out_file}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
