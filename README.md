# 2D Blueprint to 3D Model Conversion (OOPJ Project)

> An automated end-to-end pipeline that transforms 2D architectural CAD blueprint coordinates into structured Object-Oriented domain models and exports normalized 3D scene graphs.

---

## 📌 Project Overview & Team Workflow

In architectural and building information modeling (BIM), converting 2D computer-aided design (CAD) drawings into 3D environments is traditionally a manual, error-prone task. 

Our team structured this project into three decoupled, contract-driven stages ("lanes"). This modular design allows team members to develop and test their components independently using committed schema contracts and sample fixtures, avoiding blocking dependencies.

```
+------------------------------------+
|     Lane 1: Data Extraction        |  <-- Ingests CAD blueprints (DXF/DWG)
|     (2D Blueprint -> Typed Table)  |  <-- Produces typed coordinates (CSV/JSON)
+------------------------------------+
                  │
                  ▼  [Contract: schemas/lane1_input_schema.json]
+------------------------------------+
|     Lane 2: OOP Domain Model       |  <-- Parses table into polymorphic OOP hierarchy
|     (Model, Normalizer & Exporter) |  <-- Normalizes coordinates & infers missing types
+------------------------------------+  <-- Exports 3D scene graph (JSON)
                  │
                  ▼  [Contract: schemas/lane3_output_schema.json]
+------------------------------------+
|     Lane 3: 3D Scene Generation    |  <-- Handled by Lane 3 team member
|     (Blender bpy / Three.js)       |  <-- Consumes scene graph to produce 3D models
+------------------------------------+
```

> **Division of Responsibilities:**
> * **Lane 1 & Lane 2 (Covered in Detail in this Document):** Data extraction contract, OOP domain modeling, polymorphic parsing, geometric heuristic classification, spatial normalization, and scene graph serialization.
> * **Lane 3 (Under Active Development by Team Member):** Automated 3D mesh synthesis and client-side rendering (Blender `bpy` / Three.js viewer), consuming Lane 2's frozen output contract.

---

## 🏗️ Lane 1: Data Extraction (2D Blueprint → Typed Table)

### 1. The Problem Lane 1 Solves
Raw CAD coordinate exports (such as standard multileader tables) typically provide only spatial bounds (`Position X/Y/Z` and `Scale X/Y/Z`) without any semantic metadata. Downstream systems cannot distinguish whether a given set of bounding boxes represents a wall, a door, a window, or office furniture.

Lane 1 bridges this gap by parsing native CAD blueprint files (DXF/DWG using libraries such as `ezdxf`) and extracting elements into a typed, structured format.

### 2. The Data Contract (`schemas/lane1_input_schema.json`)
To ensure Lane 2 can parse extraction data without waiting for Lane 1's scripts to finish, the contract was formalized in JSON Schema.

Lane 1 emits either a **JSON payload** or a **CSV table** adhering to this schema:

| Column / Key | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `id` | String | Unique element identifier | `"wall_001"` |
| `type` | String | Semantic architectural/furniture type | `"wall"`, `"door"`, `"window"`, `"table"`, `"chair"` |
| `Position X, Y, Z` | Float | Spatial coordinate origin (in millimetres) | `33607.32, 57557.94, 0.0` |
| `Scale X, Y, Z` | Float | Bounding dimensions/length/thickness (mm) | `5000.0, 200.0, 2800.0` |
| `Rotation X, Y, Z` | Float | Euler orientation angles (degrees, default 0.0) | `0.0, 0.0, 90.0` |
| `properties` | Object | Optional metadata (e.g. `material`, `swing_direction`) | `{"exterior": true}` |

### 3. Lane 1 Fixtures & Test Data
Committed fixtures in `fixtures/` allow testing immediately without running live CAD extraction:
* [`fixtures/sample_input.json`](fixtures/sample_input.json): Structured JSON extraction with full architectural and furniture samples.
* [`fixtures/sample_input.csv`](fixtures/sample_input.csv): Tabular CSV equivalent for testing spreadsheet and CSV-based CAD extraction workflows.
* [`Data Extraction and Multileaders Sample Coordinates.csv`](Data%20Extraction%20and%20Multileaders%20Sample%20Coordinates.csv): Real-world CAD sample containing 222 multileader coordinate rows.

---

## 🏛️ Lane 2: Object-Oriented Domain Model & Transformation

### 1. Architecture & OOP Principles
Lane 2 constitutes the core software engineering layer of the project. It provides an Object-Oriented domain model that encapsulates blueprint elements, validates geometry, infers missing classification data, converts units, and serializes the 3D scene graph.

#### Class Hierarchy (`src/models/`)

```text
                        BlueprintElement (Abstract Base Class)
                       /                                      \
        ArchitecturalElement                               FurnitureElement
         /        |        \                                /      |      \
      Wall      Door     Window                          Table   Chair  GenericFurniture
```

* **Abstraction (`src/models/base.py`):**
  * `BlueprintElement` (ABC): The foundational base class. Encapsulates `element_id`, `name`, `position`, `scale`, `rotation`, and `properties`. Enforces abstract properties `element_type` and `category`, and the abstract method `get_default_material()`.
  * Common Spatial Methods:
    * `get_bounding_box()`: Computes local axis-aligned bounding bounds (`min` and `max` corners).
    * `get_center_in_world(unit_scale)`: Computes the 3D centroid in world space for accurate mesh placement.
    * `to_3d_object(unit_scale)`: Polymorphically transforms any blueprint element into a Lane 3-compliant scene object dictionary.

* **Supporting Math & Geometry Classes:**
  * `Vector3D`: Encapsulates 3D coordinate arithmetic, vector addition, unit scaling, and array/dictionary conversion.
  * `Material`: Encapsulates RGBA color, surface roughness, and metallic properties.
  * `Geometry`: Encapsulates 3D primitive geometry types (`box`, `cylinder`, `mesh`) and dimensions.
  * `Transform`: Encapsulates world-space translation, rotation, and scale.

* **Inheritance & Polymorphism:**
  * **Architectural Elements (`src/models/architectural.py`):**
    * `Wall`: Distinguishes interior vs. exterior walls; applies plaster/concrete materials.
    * `Door`: Models swing directions (`inward`/`outward`), opening clearance angles, and wood materials.
    * `Window`: Models sill heights, glazing types (`single`/`double`/`triple`), and translucent glass shaders with low surface roughness.
  * **Furniture Elements (`src/models/furniture.py`):**
    * `Table`: Models surface lengths, desk styles, and wood finish materials.
    * `Chair`: Models seating footprints, swivel capabilities, and fabric textures.
    * `GenericFurniture`: Dynamic fallback subclass for custom or unclassified interior elements.

---

### 2. Intelligent Parsing & Heuristic Classifier (`src/parser/`)

To solve the **missing element-type problem** found in legacy CAD extractions (where tables contain coordinates but no category or type), `BlueprintParser` implements a two-tier strategy:

1. **Polymorphic Factory Pattern:** If a `type` string is provided in the input, the parser dispatches to the corresponding class via its internal registry (`_TYPE_REGISTRY`).
2. **Geometric Heuristic Fallback (`infer_type_from_scale`):** If the `type` column is blank or missing, the parser evaluates bounding dimension ratios:
   * **High 2D Aspect Ratio** (Length $> 1500\text{ mm}$, Thickness $\le 400\text{ mm}$): Classified as a `Wall`.
   * **Standard Door Opening Dimensions** ($700\text{ mm} \le \text{Width} \le 1200\text{ mm}$): Classified as a `Door`.
   * **Compact Footprint** ($350\text{ mm} \le X, Y \le 700\text{ mm}$): Classified as a `Chair`.
   * **Medium/Large Surface Footprint** ($800\text{ mm} \le X \le 3000\text{ mm}$): Classified as a `Table`.
   * **Unmatched Proportions:** Instantiated safely as `GenericFurniture`.

This allows the pipeline to process raw legacy CAD tables (e.g. our 222-element CAD sample) without crashing.

---

### 3. Scene Exporter & Coordinate Normalization (`src/exporter/`)

`SceneExporter` converts the in-memory object hierarchy into the contract required by Lane 3:
* **Unit Normalization:** CAD data is typically in millimetres (`mm`), while 3D engines (Blender, Three.js, Unreal) use metres (`m`). The exporter applies scale factors ($0.001$) across positions and dimensions.
* **Global Scene Bounding Box:** Evaluates the extents of all objects and computes composite global scene bounds (`min` and `max` coordinates), allowing camera framing and lighting calculation in Lane 3.
* **Schema Conformance:** Generates output matching [`schemas/lane3_output_schema.json`](schemas/lane3_output_schema.json).

---

## 🤝 The Handoff to Lane 3 (3D Generation)

To keep Lane 3 fully independent:
* Lane 2 produces [`fixtures/sample_output.json`](fixtures/sample_output.json), which defines all objects, geometries, transforms, and materials in standard 3D scene format.
* The teammate responsible for Lane 3 can build and test their Blender `bpy` script or Three.js visualizer directly against this fixture without needing to run Lane 1 or Lane 2 code.

---

## 📁 Repository Structure

```
├── .gitignore                                      # Ignores pycache, test caches, build artifacts
├── README.md                                       # Main project documentation (this file)
├── README_LANE2.md                                 # Technical architecture notes for Lane 2
├── README_LANE3.md                                 # Specification notes for Lane 3
│
├── schemas/                                        # Pipeline data contracts (Task Zero)
│   ├── lane1_input_schema.json                     # Contract: CAD extraction -> Lane 2
│   └── lane3_output_schema.json                    # Contract: Lane 2 -> Lane 3 Scene Graph
│
├── fixtures/                                       # Decoupled mock and test data
│   ├── sample_input.json                           # Sample multi-element extraction (JSON)
│   ├── sample_input.csv                            # Sample multi-element extraction (CSV)
│   ├── sample_output.json                          # Sample generated 3D scene graph (JSON)
│   ├── generated_output.json                       # Output generated from sample_input.json
│   └── legacy_cad_output.json                      # Output generated from real 222-row CAD sample
│
├── src/                                            # Core source code
│   ├── __init__.py
│   ├── main.py                                     # Pipeline CLI entry point
│   ├── models/                                     # OOP Domain Model Hierarchy
│   │   ├── __init__.py                             # Model exports
│   │   ├── base.py                                 # Vector3D, Material, Transform, BlueprintElement ABC
│   │   ├── architectural.py                        # Wall, Door, Window
│   │   └── furniture.py                            # Table, Chair, GenericFurniture
│   ├── parser/                                     # Input Parsing & Heuristics
│   │   ├── __init__.py
│   │   └── input_parser.py                         # BlueprintParser (JSON, CSV, Heuristics)
│   └── exporter/                                   # Scene Graph Serialization
│       ├── __init__.py
│       └── scene_exporter.py                       # SceneExporter (Unit scaling, bounds, JSON)
│
├── tests/                                          # Automated Unit Test Suite (pytest)
│   ├── __init__.py
│   ├── test_models.py                              # Verifies vectors, classes, and polymorphism
│   ├── test_parser.py                              # Verifies JSON/CSV parsing & heuristic inference
│   └── test_exporter.py                            # Verifies unit conversion & scene bounds math
│
├── viewer/                                         # 3D WebGL viewer prototype for Lane 3 reference
│   ├── index.html                                  # Standalone HTML viewer
│   ├── style.css                                   # Dark-mode styling
│   └── viewer.js                                   # Three.js viewport & raycasting inspector
│
├── Data Extraction and Multileaders Sample Coordinates.csv   # Original raw CAD sample dataset
├── Data Extraction and Multileaders Sample Coordinates.xlsx  # Original raw CAD sample spreadsheet
├── Displaying data in Position, Scale.py                     # Legacy exploratory script
└── Scatterplot of X,Y,Z coordinates.py                       # Legacy matplotlib scatterplot
```

---

## 🚀 Getting Started & Execution Guide

### Prerequisites
* Python 3.10+ (Tested on Python 3.14)
* `pytest` (for running unit tests)

### 1. Installation
Clone the repository and install dependencies:
```bash
git clone https://github.com/Oxyrine/java-prototype.git
cd java-prototype
git checkout cad-pipeline
pip install pytest
```

### 2. Running the Lane 2 Pipeline CLI

Convert any input blueprint file (JSON or CSV) into a normalized 3D scene graph:

```bash
# Run against the sample JSON fixture
python src/main.py --input fixtures/sample_input.json --output fixtures/generated_output.json

# Run against the sample CSV fixture
python src/main.py --input fixtures/sample_input.csv --output fixtures/generated_csv_output.json

# Run against the raw legacy CAD dataset (invokes heuristic classification across 222 elements)
python src/main.py --input "Data Extraction and Multileaders Sample Coordinates.csv" --output "fixtures/legacy_cad_output.json"
```

#### Example CLI Output:
```text
============================================================
  Lane 2: OOP Blueprint to 3D Model Converter
============================================================
Reading input from : fixtures/sample_input.json
Successfully parsed: 8 elements.

Element Breakdown:
  - Wall        : 4
  - Door        : 1
  - Window      : 1
  - Table       : 1
  - Chair       : 1

Scene Bounding Box (in meters):
  Min: [0.0, 0.0, 0.0]
  Max: [5.2, 4.2, 2.8]

Exported 3D Scene JSON saved to: fixtures/generated_output.json
============================================================
```

### 3. Running Automated Tests

Execute the unit test suite to verify model math, polymorphic behavior, parsing, and export logic:

```bash
python -m pytest
```

---

## 👥 Summary of Completed Work

| Component | Status | Key Deliverables |
| :--- | :---: | :--- |
| **Lane 1 Data Contract** | ✅ Complete | `schemas/lane1_input_schema.json`, `fixtures/sample_input.json`, `fixtures/sample_input.csv` |
| **Lane 2 OOP Architecture** | ✅ Complete | `BlueprintElement` hierarchy, `Vector3D`, `Material`, `Wall`, `Door`, `Window`, `Table`, `Chair` |
| **Lane 2 Parser & Heuristics** | ✅ Complete | Polymorphic JSON/CSV parser with dimensional aspect-ratio heuristic classifier |
| **Lane 2 Exporter & CLI** | ✅ Complete | Spatial unit normalizer (mm $\rightarrow$ m), bounding-box calculator, `src/main.py` CLI |
| **Lane 3 Contract & Fixtures**| ✅ Complete | `schemas/lane3_output_schema.json`, `fixtures/sample_output.json` (unblocking Lane 3 member) |
| **Testing & Quality Assurance** | ✅ Complete | Automated test suite verifying data integrity and polymorphism |
| **Lane 3 Implementation** | 🔄 In Progress | Assigned to Lane 3 team member |
