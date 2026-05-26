from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.project import ProjectMaxStep, ProjectStatus


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class ProjectRead(BaseModel):
    id: int
    name: str
    status: ProjectStatus
    max_step: ProjectMaxStep = ProjectMaxStep.UPLOAD
    active_scheme_id: str | None = None
    annotation_confirmed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    cover_image_url: str | None = None

    model_config = {"from_attributes": True}
