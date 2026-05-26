from __future__ import annotations

from pydantic import BaseModel, Field


class RefineRequest(BaseModel):
    instruction: str = Field(min_length=1, max_length=4000)


class RefineDiffItem(BaseModel):
    tag: str
    text: str
    room_id: str | None = None


class RefinePreviewResponse(BaseModel):
    instruction: str
    diff: list[RefineDiffItem]
    patch: dict
    affected_room_ids: list[str]


class RefineApplyRequest(BaseModel):
    patch: dict
    affected_room_ids: list[str] = Field(default_factory=list)
    update_obsidian: bool = False
