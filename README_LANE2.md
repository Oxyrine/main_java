# Lane 2: Object-Oriented Blueprint Data Model & Scene Exporter

This module implements **Lane 2** of the **2D Blueprint to 3D Model Conversion** pipeline.

It serves as the central data contract and domain model bridge between:
* **Lane 1 (Data Extraction):** Parses CAD/DXF floor plans into typed coordinates and element descriptors.
* **Lane 3 (3D Scene Generation):** Consumes structured 3D scene definitions to generate Blender scenes or Three.js web views.

---

## The Two Core Gaps Solved

1. **Missing Element Types in Raw CAD Data:**
   * **Contract-First Solution:** Defines [`schemas/lane1_input_schema.json`](schemas/lane1_input_schema.json) requiring `type`, `position`, `scale`, and optional `rotation`.
   * **Intelligent Heuristic Fallback:** When processing legacy untyped CAD extractions (e.g. `Data Extraction and Multileaders Sample Coordinates.csv`), the `BlueprintParser` applies geometric proportion heuristics (aspect ratio, scale bounds) to infer whether an element is a wall, door, table, or chair.

2. **Hand-Placed vs. Automated 3D Scene Generation:**
   * **Scene Graph Contract:** Defines [`schemas/lane3_output_schema.json`](schemas/lane3_output_schema.json), specifying geometric primitives (`box`, `cylinder`, `mesh`), exact world bounding volumes, translation/rotation transforms, and material properties.
   * **Normalized 3D Synthesis:** Automatically translates architectural coordinates (mm) into standard 3D engine world space (meters), with computed center-offsets and composite scene bounding boxes.

---

## Object-Oriented Architecture

```text
               BlueprintElement (ABC)
             /                        \
    ArchitecturalElement             FurnitureElement
      /       |       \               /      |      \
   Wall     Door    Window         Table   Chair  GenericFurniture
```

### Core Classes (`src/models/`)
* **`Vector3D`**: Encapsulates 3D coordinate math, unit scaling, vector additions, and dictionary serialization.
* **`Material`**: Encapsulates visual properties: RGBA color, roughness, and metallic reflectance.
* **`BlueprintElement` (ABC)**:
  * Abstract base class defining common spatial properties (`position`, `scale`, `rotation`).
  * Provides abstract methods `element_type`, `category`, and `get_default_material()`.
  * Computes axis-aligned bounding boxes (`get_bounding_box()`) and centered 3D translations (`get_center_in_world()`).
  * Serializes itself polymorphically into Lane 3 format via `to_3d_object()`.
* **Architectural Hierarchy (`src/models/architectural.py`)**:
  * `Wall`: Custom materials for interior vs. exterior walls, thickness, and height.
  * `Door`: Opening directions, swing angles, and wood material properties.
  * `Window`: Glazing types, sill heights, and translucent glass materials.
* **Furniture Hierarchy (`src/models/furniture.py`)**:
  * `Table`: Desk and tabletop surface definitions.
  * `Chair`: Seating and swivel fixtures.
  * `GenericFurniture`: Dynamic fallback for unclassified interior elements.

---

## Data Contracts (Task Zero)

To allow Lane 1, Lane 2, and Lane 3 to work in complete parallel without blocking each other:

| Contract / Fixture | Description | Intended Consumer |
| :--- | :--- | :--- |
| [`schemas/lane1_input_schema.json`](schemas/lane1_input_schema.json) | JSON schema contract for CAD extraction output | Lane 1 (implementer) & Lane 2 (consumer) |
| [`schemas/lane3_output_schema.json`](schemas/lane3_output_schema.json) | JSON schema contract for 3D scene graph | Lane 2 (implementer) & Lane 3 (consumer) |
| [`fixtures/sample_input.json`](fixtures/sample_input.json) | Fixture containing walls, doors, windows, tables, chairs | Lane 2 parser verification |
| [`fixtures/sample_input.csv`](fixtures/sample_input.csv) | CSV equivalent fixture for tabular workflows | Lane 1 & Lane 2 validation |
| [`fixtures/sample_output.json`](fixtures/sample_output.json) | Reference 3D scene output | Lane 3 Blender / Three.js generator |

---

## Usage

### 1. Running the Pipeline CLI

Transform any input file (JSON or CSV) into a Lane 3 3D scene JSON:

```bash
# Process JSON blueprint fixture
python src/main.py --input fixtures/sample_input.json --output fixtures/generated_output.json

# Process CSV blueprint fixture
python src/main.py --input fixtures/sample_input.csv --output fixtures/generated_csv_output.json

# Process legacy untyped multileader coordinates from CAD
python src/main.py --input "Data Extraction and Multileaders Sample Coordinates.csv" --output "fixtures/legacy_cad_output.json"
```

### 2. Running Automated Tests

```bash
python -m pytest
```
All 12 unit tests verify:
* Vector operations, bounding box calculations, and polymorphic serialization (`tests/test_models.py`).
* JSON/CSV parsing, polymorphic factory dispatch, and heuristic type inferencing (`tests/test_parser.py`).
* Unit scaling (mm to m), scene bounds aggregation, and exporter output (`tests/test_exporter.py`).
