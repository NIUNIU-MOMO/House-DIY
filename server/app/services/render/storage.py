import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

MANIFEST_FILENAME = "manifest.json"


class RenderRecord(BaseModel):
    room_id: str
    room_name: str
    filename: str
    prompt: str
    negative: str = ""
    workflow: str = "flux_interior_t2i_api"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RenderManifest(BaseModel):
    rooms: list[RenderRecord] = Field(default_factory=list)


def get_renders_dir(project_id: int) -> Path:
    from app.services.floorplan.storage import get_project_dir

    return get_project_dir(project_id) / "renders"


def load_manifest(project_id: int) -> RenderManifest:
    path = get_renders_dir(project_id) / MANIFEST_FILENAME
    if not path.is_file():
        return RenderManifest()
    return RenderManifest.model_validate(json.loads(path.read_text(encoding="utf-8")))


def save_manifest(project_id: int, manifest: RenderManifest) -> Path:
    renders_dir = get_renders_dir(project_id)
    renders_dir.mkdir(parents=True, exist_ok=True)
    path = renders_dir / MANIFEST_FILENAME
    path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return path


def upsert_render(project_id: int, record: RenderRecord, image_bytes: bytes) -> RenderRecord:
    renders_dir = get_renders_dir(project_id)
    renders_dir.mkdir(parents=True, exist_ok=True)
    target = renders_dir / record.filename
    target.write_bytes(image_bytes)

    manifest = load_manifest(project_id)
    manifest.rooms = [item for item in manifest.rooms if item.room_id != record.room_id]
    manifest.rooms.append(record)
    save_manifest(project_id, manifest)
    return record


def get_render_path(project_id: int, room_id: str) -> Path | None:
    manifest = load_manifest(project_id)
    match = next((item for item in manifest.rooms if item.room_id == room_id), None)
    if match is None:
        return None
    path = get_renders_dir(project_id) / match.filename
    return path if path.is_file() else None
