from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.project import Project, ProjectMaxStep

MAX_STEP_ORDER: list[ProjectMaxStep] = [
    ProjectMaxStep.UPLOAD,
    ProjectMaxStep.PARSE,
    ProjectMaxStep.ANNOTATE,
    ProjectMaxStep.DESIGN,
    ProjectMaxStep.PREVIEW,
]

_STEP_INDEX = {step: index for index, step in enumerate(MAX_STEP_ORDER)}


def _coerce_max_step(step: ProjectMaxStep | str) -> ProjectMaxStep:
    if isinstance(step, ProjectMaxStep):
        return step
    return ProjectMaxStep(step)


def bump_max_step(project: Project, target: ProjectMaxStep | str) -> bool:
    """
    仅当 target 高于当前 max_step 时推进

    @param project 项目实体
    @param target 目标步骤
    @return 是否发生变更
    """
    target_step = _coerce_max_step(target)
    current_index = _STEP_INDEX[project.max_step]
    target_index = _STEP_INDEX[target_step]
    if target_index <= current_index:
        return False
    project.max_step = target_step
    return True


def bump_max_step_db(db: Session, project: Project, target: ProjectMaxStep | str) -> bool:
    """
    推进 max_step 并提交数据库

    @param db 数据库会话
    @param project 项目实体
    @param target 目标步骤
    @return 是否发生变更
    """
    changed = bump_max_step(project, target)
    if changed:
        db.add(project)
        db.commit()
        db.refresh(project)
    return changed
