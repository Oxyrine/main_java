"""Furniture domain models: Tables, Chairs, Generic Furniture."""

from typing import Any, Dict, Optional
from .base import BlueprintElement, Material, Vector3D


class FurnitureElement(BlueprintElement):
    """Base class for all non-structural furniture and interior fixtures."""

    @property
    def category(self) -> str:
        return "furniture"

    def get_default_material(self) -> Material:
        return Material(
            name="GenericFurnitureMaterial",
            color=[0.5, 0.5, 0.5, 1.0],
            roughness=0.5,
            metallic=0.1,
        )


class Table(FurnitureElement):
    """Represents tables, desks, and work surfaces."""

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
        self.style: str = self.properties.get("style", "standard")

    @property
    def element_type(self) -> str:
        return "table"

    def get_default_material(self) -> Material:
        return Material(
            name="TableMaterial",
            color=[0.40, 0.25, 0.15, 1.0],
            roughness=0.6,
            metallic=0.0,
        )


class Chair(FurnitureElement):
    """Represents chairs, stools, and seating fixtures."""

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
        self.is_swivel: bool = self.properties.get("swivel", False)

    @property
    def element_type(self) -> str:
        return "chair"

    def get_default_material(self) -> Material:
        return Material(
            name="FabricChairMaterial",
            color=[0.20, 0.30, 0.50, 1.0],
            roughness=0.8,
            metallic=0.0,
        )


class GenericFurniture(FurnitureElement):
    """Fallback class for generic or unclassified interior elements."""

    def __init__(
        self,
        element_id: str,
        type_name: str = "furniture",
        name: Optional[str] = None,
        position: Optional[Vector3D] = None,
        scale: Optional[Vector3D] = None,
        rotation: Optional[Vector3D] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(element_id, name, position, scale, rotation, properties)
        self._type_name = type_name

    @property
    def element_type(self) -> str:
        return self._type_name
