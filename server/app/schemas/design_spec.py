from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field


class FurniturePlacement(BaseModel):
    sku: str
    wall: str
    offset: list[float] = Field(min_length=2, max_length=2)
    rotation: float = 0.0


class Render2DSpec(BaseModel):
    prompt: str
    negative: str = "blurry, distorted, watermark"
    workflow: str = "flux_interior_t2i_api"
    controlnet: str | None = "layout_depth"


class Render3DSpec(BaseModel):
    floorMaterial: str = "oak_light"
    wallMaterial: str = "paint_warm_white"
    ceilingHeight: float = 2.8
    lighting: str = "day_soft"


class RoomDesignSpec(BaseModel):
    id: str
    name: str
    style: str
    palette: list[str] = Field(default_factory=list)
    furniture: list[FurniturePlacement] = Field(default_factory=list)
    render2d: Render2DSpec
    render3d: Render3DSpec = Field(default_factory=Render3DSpec)


class DesignSpec(BaseModel):
    version: int = 1
    globalStyle: str
    ragContextIds: list[str] = Field(default_factory=list)
    rooms: Annotated[list[RoomDesignSpec], Field(min_length=1)]


class DesignGenerateRequest(BaseModel):
    brief: str = Field(min_length=1, max_length=4000)
    global_style: str | None = None
    use_rag: bool = True
