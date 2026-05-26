from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.task import TaskStatus, TaskType


class TaskRead(BaseModel):
    id: int
    project_id: int
    type: TaskType
    status: TaskStatus
    progress: float
    step: int
    step_label: str
    retry_count: int
    payload: str | None
    error: str | None
    logs: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
