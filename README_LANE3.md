# Lane 3: 3D Scene Generation (Blender & Three.js)

This module implements **Lane 3** of the **2D Blueprint to 3D Model Conversion** pipeline.

It consumes the structured 3D scene definition exported by Lane 2 ([`schemas/lane3_output_schema.json`](schemas/lane3_output_schema.json)) and generates real, automated 3D visual models.

---

## Deliverables

We provide two production-grade solutions for 3D generation:

### 1. Automated Blender Generator (`src/generators/blender_generator.py`)
Generates native `.blend` 3D files directly from JSON:
* Automatically clears the scene and instantiates meshes matching exact dimensions and transforms.
* Creates materials with Principled BSDF nodes (base color, roughness, metallic, and glass transmission).
* Positions sunlight and architectural camera to frame the scene's bounding box.
* Can be run headless from CLI or within Blender's Scripting workspace.

#### How to Run with Blender:
```bash
# Headless batch generation:
blender --background --python src/generators/blender_generator.py -- fixtures/generated_output.json output_scene.blend

# Or directly in Python (to validate/inspect scene parameters):
python src/generators/blender_generator.py fixtures/generated_output.json
```

---

### 2. Interactive Three.js 3D Web Viewer (`viewer/`)
An interactive WebGL 3D viewer that runs in any web browser without needing Blender installed:
* **Interactive Orbit & Pan:** Inspect the generated building and furniture in 3D.
* **Camera Modes:** Switch between 3D Orbit Perspective and 2D Top-Down Blueprint Plan.
* **Element Raycasting & Inspector:** Click any wall, door, window, or table to view its ID, dimensions, position, and metadata.
* **Layer Toggles:** Dynamically toggle Architectural elements, Furniture, or Wireframe rendering.
* **File Upload Support:** Drag-and-drop or load any exported Lane 2 JSON file on the fly.

#### How to Launch the Web Viewer:
Simply open [`viewer/index.html`](viewer/index.html) in your web browser, or serve locally:
```bash
python -m http.server 8000 --directory viewer
```
Then visit `http://localhost:8000`.

---

## Verification & Testing

Run the automated test suite verifying Lane 3 schema adherence and scene building:
```bash
python -m pytest tests/test_lane3.py
```
