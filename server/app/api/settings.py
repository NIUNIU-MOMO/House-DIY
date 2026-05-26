from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.settings_storage import (
    StorageSettings,
    check_output_root_writable,
    load_storage_settings,
    resolve_output_root,
    save_storage_settings,
)

router = APIRouter(prefix="/settings", tags=["settings"])


class StorageSettingsRead(BaseModel):
    output_root: str
    effective_output_root: str
    writable: bool
    writable_error: str | None = None


class StorageSettingsUpdate(BaseModel):
    output_root: str = Field(min_length=1)


@router.get("/storage", response_model=StorageSettingsRead)
def get_storage_settings():
    settings = load_storage_settings()
    effective = resolve_output_root()
    writable, error = check_output_root_writable(effective)
    return StorageSettingsRead(
        output_root=settings.output_root,
        effective_output_root=str(effective),
        writable=writable,
        writable_error=error,
    )


@router.put("/storage", response_model=StorageSettingsRead)
def put_storage_settings(payload: StorageSettingsUpdate):
    save_storage_settings(StorageSettings(output_root=payload.output_root))
    effective = resolve_output_root()
    writable, error = check_output_root_writable(effective)
    return StorageSettingsRead(
        output_root=payload.output_root,
        effective_output_root=str(effective),
        writable=writable,
        writable_error=error,
    )
