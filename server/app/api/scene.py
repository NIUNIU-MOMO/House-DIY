from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.project import Project
from app.schemas.scene import ScenePackageRead
from app.services.scene_builder import get_scene_gltf_path, load_scene_package

router = APIRouter(prefix="/projects/{project_id}/scene", tags=["scene"])


def _get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.get("", response_model=ScenePackageRead)
def get_scene(project_id: int, db: Session = Depends(get_db)):
    _get_project_or_404(project_id, db)
    package = load_scene_package(project_id)
    if package is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene not found")
    return ScenePackageRead(
        version=package.version,
        gltf=package.gltf,
        status=package.status,
        gltf_url=f"/api/v1/projects/{project_id}/scene/gltf",
        rooms=package.rooms,
        portals=package.portals,
        active_room=package.active_room,
    )


@router.get("/gltf")
def get_scene_gltf(project_id: int, db: Session = Depends(get_db)):
    _get_project_or_404(project_id, db)
    path = get_scene_gltf_path(project_id)
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene glTF not found")
    return FileResponse(path, media_type="model/gltf+json")
