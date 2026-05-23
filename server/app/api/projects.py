from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.project import Project, ProjectStatus
from app.schemas.project import ProjectCreate, ProjectRead
from app.services.render.storage import resolve_cover_image_url

router = APIRouter(prefix="/projects", tags=["projects"])


def _project_to_read(project: Project) -> ProjectRead:
    cover_image_url = None
    if project.status == ProjectStatus.DELIVERED:
        cover_image_url = resolve_cover_image_url(project.id)
    return ProjectRead(
        id=project.id,
        name=project.name,
        status=project.status,
        created_at=project.created_at,
        updated_at=project.updated_at,
        cover_image_url=cover_image_url,
    )


@router.get("", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.updated_at.desc()).all()
    return [_project_to_read(project) for project in projects]


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(name=payload.name, status=ProjectStatus.DRAFT)
    db.add(project)
    db.commit()
    db.refresh(project)
    return _project_to_read(project)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return _project_to_read(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    db.delete(project)
    db.commit()
