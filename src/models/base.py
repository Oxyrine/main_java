"""Base Object-Oriented representations for blueprint elements and 3D transformations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Vector3D:
    """Represents a 3D coordinate, scale, or Euler rotation vector."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def scaled_by(self, factor: float) -> "Vector3D":
        """Return a new Vector3D scaled uniformly by factor."""
        return Vector3D(self.x * factor, self.y * factor, self.z * factor)

    def add(self, other: "Vector3D") -> "Vector3D":
        """Add another Vector3D component-wise."""
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def to_dict(self) -> Dict[str, float]:
        """Convert vector to dictionary."""
        return {"x": round(self.x, 4), "y": round(self.y, 4), "z": round(self.z, 4)}

    def to_list(self) -> List[float]:
        """Convert vector to [x, y, z] list."""
        return [round(self.x, 4), round(self.y, 4), round(self.z, 4)]


@dataclass
class Material:
    """Visual material attributes for 3D generation."""
    name: str
    color: List[float] = field(default_factory=lambda: [0.8, 0.8, 0.8, 1.0])
    roughness: float = 0.5
    metallic: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "color": self.color,
            "roughness": self.roughness,
            "metallic": self.metallic,
        }


@dataclass
class Geometry:
    """Geometric primitive definition."""
    primitive: str  # e.g., 'box', 'plane', 'cylinder', 'mesh'
    dimensions: Vector3D

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primitive": self.primitive,
            "dimensions": {
                "width": round(self.dimensions.x, 4),
                "depth": round(self.dimensions.y, 4),
                "height": round(self.dimensions.z, 4),
            },
        }


@dataclass
class Transform:
    """Local or world transform for 3D rendering."""
    translation: Vector3D
    rotation: Vector3D
    scale: Vector3D

    def to_dict(self) -> Dict[str, Any]:
        return {
            "translation": self.translation.to_dict(),
            "rotation": self.rotation.to_dict(),
            "scale": self.scale.to_dict(),
        }


class BlueprintElement(ABC):
    """
    Abstract Base Class for all 2D blueprint elements.
    Encapsulates core spatial parameters, element metadata, and 3D object synthesis.
    """

    def __init__(
        self,
        element_id: str,
        name: Optional[str] = None,
        position: Optional[Vector3D] = None,
        scale: Optional[Vector3D] = None,
        rotation: Optional[Vector3D] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.element_id: str = element_id
        self.name: str = name or f"{self.__class__.__name__}_{element_id}"
        self.position: Vector3D = position or Vector3D()
        self.scale: Vector3D = scale or Vector3D(1.0, 1.0, 1.0)
        self.rotation: Vector3D = rotation or Vector3D()
        self.properties: Dict[str, Any] = properties or {}

    @property
    @abstractmethod
    def element_type(self) -> str:
        """Returns the specific element type name (e.g. 'wall', 'door', 'chair')."""
        pass

    @property
    @abstractmethod
    def category(self) -> str:
        """Returns the high-level category (e.g. 'architectural', 'furniture')."""
        pass

    @abstractmethod
    def get_default_material(self) -> Material:
        """Return the default material for this element."""
        pass

    def get_geometry_primitive(self) -> str:
        """Return the 3D geometric primitive name. Defaults to 'box'."""
        return "box"

    def get_bounding_box(self) -> Tuple[Vector3D, Vector3D]:
        """Compute the axis-aligned bounding box (min_corner, max_corner) in input units."""
        min_corner = Vector3D(
            min(self.position.x, self.position.x + self.scale.x),
            min(self.position.y, self.position.y + self.scale.y),
            min(self.position.z, self.position.z + self.scale.z),
        )
        max_corner = Vector3D(
            max(self.position.x, self.position.x + self.scale.x),
            max(self.position.y, self.position.y + self.scale.y),
            max(self.position.z, self.position.z + self.scale.z),
        )
        return min_corner, max_corner

    def get_center_in_world(self, unit_scale: float = 1.0) -> Vector3D:
        """
        Calculate the center position (translation) of the 3D bounding volume.
        In 3D engines (Blender/Three.js), box primitives are typically centered at origin
        and rotated around their center. We rotate the local half-dimension offset by rotation.z.
        """
        import math
        rad_z = math.radians(self.rotation.z)
        hx = self.scale.x / 2.0
        hy = self.scale.y / 2.0
        hz = self.scale.z / 2.0

        # Rotate the local (hx, hy) center vector by rotation.z
        dx = hx * math.cos(rad_z) - hy * math.sin(rad_z)
        dy = hx * math.sin(rad_z) + hy * math.cos(rad_z)

        return Vector3D(
            (self.position.x + dx) * unit_scale,
            (self.position.y + dy) * unit_scale,
            (self.position.z + hz) * unit_scale,
        )

    def to_3d_object(self, unit_scale: float = 1.0) -> Dict[str, Any]:
        """
        Convert this BlueprintElement into a structured 3D scene object dict for Lane 3.
        
        :param unit_scale: Factor to convert input units (e.g., mm) to target 3D units (e.g., m).
        """
        # Dimensions in target units
        dims = Vector3D(
            abs(self.scale.x) * unit_scale,
            abs(self.scale.y) * unit_scale,
            abs(self.scale.z) * unit_scale,
        )
        center = self.get_center_in_world(unit_scale)

        geometry = Geometry(primitive=self.get_geometry_primitive(), dimensions=dims)
        transform = Transform(
            translation=center,
            rotation=self.rotation,
            scale=Vector3D(1.0, 1.0, 1.0),
        )
        material = self.get_default_material()

        meta = dict(self.properties)
        meta["raw_id"] = self.element_id

        return {
            "id": self.element_id,
            "name": self.name,
            "category": self.category,
            "type": self.element_type,
            "geometry": geometry.to_dict(),
            "transform": transform.to_dict(),
            "material": material.to_dict(),
            "metadata": meta,
        }

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} id={self.element_id} "
            f"pos=({self.position.x}, {self.position.y}, {self.position.z}) "
            f"scale=({self.scale.x}, {self.scale.y}, {self.scale.z})>"
        )
