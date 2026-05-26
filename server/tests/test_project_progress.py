import pytest

from app.models.project import Project, ProjectMaxStep, ProjectStatus
from app.services.project_progress import bump_max_step


@pytest.fixture
def project(db_session):
    item = Project(name="进度测试", status=ProjectStatus.DRAFT, max_step=ProjectMaxStep.UPLOAD)
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


def test_bump_max_step_only_increases(project):
    assert not bump_max_step(project, ProjectMaxStep.UPLOAD)
    assert project.max_step == ProjectMaxStep.UPLOAD

    assert bump_max_step(project, ProjectMaxStep.PARSE)
    assert project.max_step == ProjectMaxStep.PARSE

    assert not bump_max_step(project, ProjectMaxStep.PARSE)
    assert bump_max_step(project, ProjectMaxStep.ANNOTATE)
    assert project.max_step == ProjectMaxStep.ANNOTATE


def test_bump_max_step_never_decreases(project):
    project.max_step = ProjectMaxStep.DESIGN
    assert not bump_max_step(project, ProjectMaxStep.ANNOTATE)
    assert project.max_step == ProjectMaxStep.DESIGN


def test_bump_max_step_accepts_string(project):
    assert bump_max_step(project, "parse")
    assert project.max_step == ProjectMaxStep.PARSE
