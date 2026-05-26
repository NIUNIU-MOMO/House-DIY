from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ProjectStatus(str, enum.Enum):
    DRAFT = "draft"
    PARSING = "parsing"
    REVIEW = "review"
    DESIGNING = "designing"
    DELIVERED = "delivered"


class ProjectMaxStep(str, enum.Enum):
    UPLOAD = "upload"
    PARSE = "parse"
    ANNOTATE = "annotate"
    DESIGN = "design"
    PREVIEW = "preview"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus),
        default=ProjectStatus.DRAFT,
        nullable=False,
    )
    max_step: Mapped[ProjectMaxStep] = mapped_column(
        Enum(ProjectMaxStep, values_callable=lambda obj: [item.value for item in obj]),
        default=ProjectMaxStep.UPLOAD,
        nullable=False,
    )
    active_scheme_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    annotation_confirmed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
