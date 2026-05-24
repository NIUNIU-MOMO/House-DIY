from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

from app.services.floorplan.plan_classifier import PlanType


class FloorPlanStatus(str, Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"


class OpeningType(str, Enum):
    DOOR = "door"
    WINDOW = "window"


class ValidationIssue(BaseModel):
    code: str
    severity: Literal["error", "warning", "info"]
    message: str
    room_ids: list[str] = Field(default_factory=list)


class FloorPlanValidation(BaseModel):
    level: Literal["pass", "warning", "error", "unknown"] = "unknown"
    checked_at: str | None = None
    issues: list[ValidationIssue] = Field(default_factory=list)


class ParseMeta(BaseModel):
    vlm_model: str | None = None
    vlm_steps: int | None = None
    cv_wall_quality: float | None = None
    wall_source: Literal["cv", "polygon"] | None = None


class Point(BaseModel):
    x: float
    y: float


class Wall(BaseModel):
    id: str
    points: Annotated[list[Point], Field(min_length=2)]
    thickness: float = 0.2


class Room(BaseModel):
    id: str
    name: str
    polygon: Annotated[list[Point], Field(min_length=3)]
    area: float | None = None


class Opening(BaseModel):
    id: str
    type: OpeningType
    wall_id: str
    position: Annotated[float, Field(ge=0, le=1)]
    width: float = Field(gt=0)
    connects: list[str] = Field(default_factory=list)


class FloorPlanModel(BaseModel):
    scale: float | None = Field(default=None, gt=0)
    walls: list[Wall] = Field(default_factory=list)
    rooms: list[Room] = Field(default_factory=list)
    openings: list[Opening] = Field(default_factory=list)
    status: FloorPlanStatus = FloorPlanStatus.DRAFT
    plan_type: PlanType | None = None
    validation: FloorPlanValidation | None = None
    parse_meta: ParseMeta | None = None

    @model_validator(mode="after")
    def validate_walls_for_confirmed(self) -> "FloorPlanModel":
        if self.status == FloorPlanStatus.CONFIRMED and not self.walls:
            raise ValueError("walls must not be empty when status is confirmed")
        return self


class FloorPlanRead(FloorPlanModel):
    source_image: str | None = None
    original_filename: str | None = None
    estimated_area: float | None = None
    source_url: str | None = None
    source_width: int | None = None
    source_height: int | None = None
    has_watermark: bool | None = None
    plan_type_label: str | None = None
    plan_type_message: str | None = None


class ScaleRequest(BaseModel):
    point_a: Point
    point_b: Point
    distance_m: float = Field(gt=0)
