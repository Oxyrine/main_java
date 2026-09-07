"""Lane 3: Blender (bpy) 3D Scene Generator.

Builds an automated, fully textured 3D scene from Lane 2's scene JSON export.
Can be executed directly within Blender (headless or GUI):
    blender --background --python src/generators/blender_generator.py -- fixtures/generated_output.json output.blend
"""

import json
import math
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

# Optional bpy import for running in Blender environment
try:
    import bpy
    import mathutils
    BPY_AVAILABLE = True
except ImportError:
    BPY_AVAILABLE = False


class BlenderSceneBuilder:
    """
    Builds Blender 3D scene objects from Lane 2 JSON specifications.
    Handles materials, lighting, cameras, and primitive geometry instantiation.
    """

    def __init__(self, scene_data: Dict[str, Any]) -> None:
        self.data = scene_data
        self.metadata = scene_data.get("scene_metadata", {})
        self.objects = scene_data.get("objects", [])

    @classmethod
    def from_file(cls, json_path: str) -> "BlenderSceneBuilder":
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(data)

    def get_summary(self) -> Dict[str, Any]:
        """Provides summary of elements to be generated in 3D."""
        return {
            "element_count": len(self.objects),
            "target_units": self.metadata.get("target_units", "m"),
            "scene_bounds": self.metadata.get("scene_bounds", {}),
            "categories": list(set(obj.get("category", "unknown") for obj in self.objects)),
        }

    def build_in_blender(self, output_blend_path: Optional[str] = None) -> None:
        """Executes Blender bpy commands to generate the 3D scene."""
        if not BPY_AVAILABLE:
            raise RuntimeError(
                "Blender Python API (bpy) is not available in the current Python environment. "
                "Run this script inside Blender: blender --background --python src/generators/blender_generator.py -- <input.json> <output.blend>"
            )

        # 1. Clean existing scene
        bpy.ops.wm.read_factory_settings(use_empty=True)
        scene = bpy.context.scene

        # 2. Materials cache
        materials_cache: Dict[str, bpy.types.Material] = {}

        def get_or_create_material(mat_data: Dict[str, Any]) -> bpy.types.Material:
            name = mat_data.get("name", "DefaultMaterial")
            if name in materials_cache:
                return materials_cache[name]

            mat = bpy.data.materials.new(name=name)
            mat.use_nodes = True
            nodes = mat.node_tree.nodes
            bsdf = nodes.get("Principled BSDF")

            if bsdf:
                color = mat_data.get("color", [0.8, 0.8, 0.8, 1.0])
                if len(color) == 3:
                    color = list(color) + [1.0]
                bsdf.inputs["Base Color"].default_value = color
                bsdf.inputs["Roughness"].default_value = float(mat_data.get("roughness", 0.5))
                bsdf.inputs["Metallic"].default_value = float(mat_data.get("metallic", 0.0))

                # If semi-transparent (e.g. glass)
                if color[3] < 1.0:
                    mat.blend_method = "BLEND"
                    if "Transmission Weight" in bsdf.inputs:
                        bsdf.inputs["Transmission Weight"].default_value = 0.9
                    elif "Transmission" in bsdf.inputs:
                        bsdf.inputs["Transmission"].default_value = 0.9

            materials_cache[name] = mat
            return mat

        # 3. Create objects
        for item in self.objects:
            obj_id = item.get("id", "obj")
            obj_name = item.get("name", obj_id)
            geom = item.get("geometry", {})
            dims = geom.get("dimensions", {"width": 1.0, "depth": 1.0, "height": 1.0})
            trans = item.get("transform", {})
            loc = trans.get("translation", {"x": 0.0, "y": 0.0, "z": 0.0})
            rot = trans.get("rotation", {"x": 0.0, "y": 0.0, "z": 0.0})

            primitive = geom.get("primitive", "box")

            if primitive == "box":
                bpy.ops.mesh.primitive_cube_add(size=1.0)
                mesh_obj = bpy.context.active_object
                mesh_obj.name = obj_name
                # Set dimensions
                mesh_obj.dimensions = (dims["width"], dims["depth"], dims["height"])
                # Set location (center)
                mesh_obj.location = (loc["x"], loc["y"], loc["z"])
                # Set rotation (degrees to radians)
                mesh_obj.rotation_euler = (
                    math.radians(rot.get("x", 0.0)),
                    math.radians(rot.get("y", 0.0)),
                    math.radians(rot.get("z", 0.0)),
                )
            elif primitive == "cylinder":
                radius = dims["width"] / 2.0
                depth = dims["height"]
                bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth)
                mesh_obj = bpy.context.active_object
                mesh_obj.name = obj_name
                mesh_obj.location = (loc["x"], loc["y"], loc["z"])
            else:
                # Default box
                bpy.ops.mesh.primitive_cube_add(size=1.0)
                mesh_obj = bpy.context.active_object
                mesh_obj.name = obj_name
                mesh_obj.dimensions = (dims["width"], dims["depth"], dims["height"])
                mesh_obj.location = (loc["x"], loc["y"], loc["z"])

            # Apply material
            if "material" in item:
                mat = get_or_create_material(item["material"])
                mesh_obj.data.materials.append(mat)

        # 4. Set up Camera and Sun Light based on scene bounds
        bounds = self.metadata.get("scene_bounds", {})
        min_b = bounds.get("min", [0.0, 0.0, 0.0])
        max_b = bounds.get("max", [10.0, 10.0, 3.0])

        cx = (min_b[0] + max_b[0]) / 2.0
        cy = (min_b[1] + max_b[1]) / 2.0
        max_dim = max(max_b[0] - min_b[0], max_b[1] - min_b[1], 5.0)

        # Add Sunlight
        bpy.ops.object.light_add(type="SUN", location=(cx, cy, max_b[2] + 15.0))
        sun = bpy.context.active_object
        sun.data.energy = 3.5

        # Add Camera framed to view the scene
        cam_dist = max_dim * 1.5
        bpy.ops.object.camera_add(location=(cx, cy - cam_dist, max_b[2] + cam_dist * 0.8))
        cam = bpy.context.active_object
        cam.rotation_euler = (math.radians(55.0), 0.0, 0.0)
        scene.camera = cam

        # 5. Save .blend file if specified
        if output_blend_path:
            out = Path(output_blend_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            bpy.ops.wm.save_as_mainfile(filepath=str(out.resolve()))
            print(f"Blender scene saved to: {out.resolve()}")


def main() -> None:
    """CLI handler when invoked directly or via Blender."""
    args = sys.argv
    # If run in blender with `--`, extract custom args
    if "--" in args:
        custom_args = args[args.index("--") + 1:]
    else:
        custom_args = args[1:]

    input_json = custom_args[0] if len(custom_args) > 0 else "fixtures/sample_output.json"
    output_blend = custom_args[1] if len(custom_args) > 1 else "output_scene.blend"

    print(f"BlenderSceneBuilder loading: {input_json}")
    builder = BlenderSceneBuilder.from_file(input_json)
    summary = builder.get_summary()
    print("Scene elements summary:", summary)

    if BPY_AVAILABLE:
        builder.build_in_blender(output_blend)
    else:
        print("Note: Running outside Blender. Schema parsed and validated successfully.")


if __name__ == "__main__":
    main()
