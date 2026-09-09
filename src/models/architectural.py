"""Architectural domain models: Walls, Doors, Windows."""

from typing import Any, Dict, Optional
from .base import BlueprintElement, Material, Vector3D


class ArchitecturalElement(BlueprintElement):
    """Base class for all architectural building elements (walls, openings, floors, roofs)."""

    @property
    def category(self) -> str:
        return "architectural"


class Wall(ArchitecturalElement):
    """Represents a wall segment in the architectural plan."""

    def __init__(
        self,
        element_id: str,
        name: Optional[str] = None,
        position: Optional[Vector3D] = None,
        scale: Optional[Vector3D] = None,
        rotation: Optional[Vector3D] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(element_id, name, position, scale, rotation, properties)
        # Identify if exterior or interior
        self.is_exterior: bool = self.properties.get("exterior", True)
        self.material_type: str = self.properties.get("material", "concrete")

    @property
    def element_type(self) -> str:
        return "wall"

    def get_default_material(self) -> Material:
        if self.is_exterior:
            return Material(
                name="ExteriorWallMaterial",
                color=[0.82, 0.82, 0.80, 1.0],
                roughness=0.75,
                metallic=0.0,
            )
        return Material(
            name="InteriorWallMaterial",
            color=[0.92, 0.92, 0.90, 1.0],
            roughness=0.6,
            metallic=0.0,
        )


class Door(ArchitecturalElement):
    """Represents a door opening or door leaf in the plan."""

    def __init__(
        self,
        element_id: str,
        name: Optional[str] = None,
        position: Optional[Vector3D] = None,
        scale: Optional[Vector3D] = None,
        rotation: Optional[Vector3D] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(element_id, name, position, scale, rotation, properties)
        self.swing_direction: str = self.properties.get("swing_direction", "inward")
        self.open_angle: float = float(self.properties.get("open_angle", 0.0))

    @property
    def element_type(self) -> str:
        return "door"

    def get_default_material(self) -> Material:
        return Material(
            name="WoodDoorMaterial",
            color=[0.55, 0.35, 0.20, 1.0],
            roughness=0.45,
            metallic=0.05,
        )


class Window(ArchitecturalElement):
    """Represents a window opening or glazed unit in the plan."""

    def __init__(
        self,
        element_id: str,
        name: Optional[str] = None,
        position: Optional[Vector3D] = None,
        scale: Optional[Vector3D] = None,
        rotation: Optional[Vector3D] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(element_id, name, position, scale, rotation, properties)
        self.sill_height: float = float(self.properties.get("sill_height", self.position.z))
        self.glazing: str = self.properties.get("glazing", "double")

    @property
    def element_type(self) -> str:
        return "window"

    def get_default_material(self) -> Material:
        return Material(
            name="GlassMaterial",
            color=[0.60, 0.80, 0.90, 0.4],
            roughness=0.1,
            metallic=0.1,
        )


class Floor(ArchitecturalElement):
    """Represents a floor slab for an enclosed architectural room."""

    def __init__(
        self,
        element_id: str,
        name: Optional[str] = None,
        position: Optional[Vector3D] = None,
        scale: Optional[Vector3D] = None,
        rotation: Optional[Vector3D] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(element_id, name, position, scale, rotation, properties)
        self.room_type: str = self.properties.get("room_type", "room")
        self.room_id: str = self.properties.get("room_id", element_id)

    @property
    def element_type(self) -> str:
        return "floor"

    def get_default_material(self) -> Material:
        palette = {
            "living": [0.85, 0.82, 0.78, 1.0],
            "bedroom": [0.82, 0.84, 0.88, 1.0],
            "kitchen": [0.88, 0.88, 0.86, 1.0],
            "bathroom": [0.72, 0.82, 0.88, 1.0],
            "sauna": [0.82, 0.60, 0.35, 1.0],
            "utility": [0.75, 0.82, 0.85, 1.0],
            "entry": [0.78, 0.76, 0.74, 1.0],
            "balcony": [0.75, 0.75, 0.75, 1.0],
        }
        color = palette.get(self.room_type, [0.84, 0.84, 0.82, 1.0])
        return Material(
            name=f"FloorMaterial_{self.room_type.capitalize()}",
            color=color,
            roughness=0.5,
            metallic=0.02,
        )

