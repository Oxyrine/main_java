"""Flask Web Application for Interactive 2D Blueprint to 3D Model Conversion.

Serves the WebGL 3D viewer and provides REST endpoints to upload DXF/CSV/JSON blueprints,
convert them through the 3-lane pipeline, and visualize the 3D scene in real-time.
"""

import os
from pathlib import Path
import sys
import tempfile

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from flask import Flask, jsonify, request, send_from_directory
from src.pipeline import BlueprintTo3DPipeline

app = Flask(__name__, static_folder="viewer")
pipeline = BlueprintTo3DPipeline()


@app.route("/")
def index():
    """Serve the main WebGL viewer application."""
    return send_from_directory("viewer", "index.html")


@app.route("/<path:path>")
def static_proxy(path):
    """Serve viewer static assets (viewer.js, style.css, etc.)."""
    return send_from_directory("viewer", path)


@app.route("/api/convert", methods=["POST"])
def convert_blueprint():
    """
    Accepts an uploaded blueprint file (.dxf, .csv, .json),
    executes the 3-lane pipeline, and returns the generated 3D scene graph.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded. Please attach a blueprint file."}), 400

    uploaded = request.files["file"]
    if uploaded.filename == "":
        return jsonify({"error": "Empty filename provided."}), 400

    filename = uploaded.filename
    suffix = Path(filename).suffix.lower()

    ALLOWED_EXTENSIONS = [".dxf", ".csv", ".json", ".txt", ".png", ".jpg", ".jpeg", ".bmp", ".webp"]
    if suffix not in ALLOWED_EXTENSIONS:
        return jsonify({
            "error": f"Unsupported file extension '{suffix}'. Supported: .dxf, .csv, .json, .png, .jpg"
        }), 400

    # Save to a temporary file for pipeline processing
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_f:
        temp_path = Path(temp_f.name)
        uploaded.save(temp_path)

    vision_cfg = None
    if suffix in [".png", ".jpg", ".jpeg", ".bmp", ".webp"]:
        from src.vision.config import VisionConfig
        vision_cfg = VisionConfig(
            mm_per_px=request.form.get("mm_per_px", type=float),
            known_width_mm=request.form.get("known_width_mm", type=float),
            free_angle=request.form.get("free_angle", default="false").lower() in ("true", "1", "yes"),
            enable_ocr=request.form.get("enable_ocr", default="true").lower() in ("true", "1", "yes"),
        )

    try:
        result = pipeline.process(temp_path, vision_config=vision_cfg)
        return jsonify({
            "success": True,
            "filename": filename,
            "element_count": result.element_count,
            "element_types": result.element_types,
            "duration_ms": result.duration_ms,
            "scene_data": result.scene_data,
        })
    except Exception as e:
        return jsonify({"error": f"Conversion failed: {str(e)}"}), 500
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


@app.route("/api/sample", methods=["GET"])
def get_sample_scene():
    """Returns the reference sample scene JSON."""
    sample_path = REPO_ROOT / "fixtures" / "sample_output.json"
    if sample_path.exists():
        return send_from_directory(sample_path.parent, sample_path.name)
    return jsonify({"error": "Sample scene not found"}), 404


@app.route("/api/legacy", methods=["GET"])
def get_legacy_cad_scene():
    """Returns the 222-element legacy CAD scene JSON."""
    legacy_path = REPO_ROOT / "fixtures" / "legacy_cad_output.json"
    if legacy_path.exists():
        return send_from_directory(legacy_path.parent, legacy_path.name)
    return jsonify({"error": "Legacy CAD scene not found"}), 404


@app.route("/api/residential", methods=["GET"])
def get_residential_scene():
    """Returns the 40-element residential vision floor plan scene JSON."""
    res_path = REPO_ROOT / "fixtures" / "residential_scene.json"
    if res_path.exists():
        return send_from_directory(res_path.parent, res_path.name)
    return jsonify({"error": "Residential scene not found"}), 404


@app.route("/api/synthetic", methods=["GET"])
def get_synthetic_scene():
    """Returns the 28-element synthetic 3-room floor plan scene JSON."""
    syn_path = REPO_ROOT / "fixtures" / "synthetic_scene.json"
    if syn_path.exists():
        return send_from_directory(syn_path.parent, syn_path.name)
    return jsonify({"error": "Synthetic scene not found"}), 404


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Blueprint-to-3D Web App on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
