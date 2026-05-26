from __future__ import annotations

from pydantic import BaseModel, Field


class Vec3(BaseModel):
    x: float
    y: float
    z: float


class Bounds3D(BaseModel):
    min: Vec3
    max: Vec3


class CollisionBox(BaseModel):
    min: list[float] = Field(min_length=3, max_length=3)
    max: list[float] = Field(min_length=3, max_length=3)


class SceneFurnitureItem(BaseModel):
    sku: str
    name: str
    position: list[float] = Field(min_length=3, max_length=3)
    rotation: float = 0.0
    size: list[float] = Field(min_length=3, max_length=3)


class ScenePortal(BaseModel):
    id: str
    source_room_id: str
    target_room_id: str
    target_room_name: str
    trigger: CollisionBox
    spawn: list[float] = Field(min_length=3, max_length=3)


class SceneRoomMeta(BaseModel):
    id: str
    name: str
    bounds: Bounds3D
    collision_boxes: list[CollisionBox] = Field(default_factory=list)
    furniture: list[SceneFurnitureItem] = Field(default_factory=list)
    portals: list[ScenePortal] = Field(default_factory=list)


class ScenePackage(BaseModel):
    version: int = 1
    gltf: str = "scene.gltf"
    status: str = "ready"
    rooms: list[SceneRoomMeta] = Field(default_factory=list)
    portals: list[ScenePortal] = Field(default_factory=list)
    active_room: str | None = None


class ScenePackageRead(BaseModel):
    version: int
    gltf: str
    status: str
    gltf_url: str
    rooms: list[SceneRoomMeta]
    portals: list[ScenePortal]
    active_room: str | None
