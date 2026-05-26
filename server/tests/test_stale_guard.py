import pytest

from app.schemas.floorplan import FloorPlanModel, FloorPlanStatus
from app.services.design import scheme_storage
from app.services.floorplan import storage
from app.services.stale_guard import (
    check_design_operation_allowed,
    clear_annotation_stale,
    is_annotation_stale,
    mark_annotation_stale,
    StaleDesignBlocked,
)


@pytest.fixture
def project_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.floorplan.storage.settings.house_diy_projects_dir", str(tmp_path))
    monkeypatch.setattr(
        "app.services.settings_storage.resolve_output_root",
        lambda env_fallback=None: tmp_path,
    )
    return tmp_path


def _seed_floorplan(project_id: int, confirmed: bool = False) -> None:
    storage.ensure_project_dir(project_id)
    status = FloorPlanStatus.CONFIRMED if confirmed else FloorPlanStatus.DRAFT
    walls = [
        {"id": "w1", "points": [{"x": 0, "y": 0}, {"x": 100, "y": 0}], "thickness": 0.2},
    ]
    rooms = [
        {
            "id": "r1",
            "name": "客厅",
            "polygon": [
                {"x": 0, "y": 0},
                {"x": 100, "y": 0},
                {"x": 100, "y": 100},
                {"x": 0, "y": 100},
            ],
            "area": 10.0,
        }
    ]
    storage.save_floorplan(
        project_id,
        FloorPlanModel(status=status, walls=walls, rooms=rooms, openings=[]),
    )


def test_mark_annotation_stale(project_dir):
    _seed_floorplan(1)
    scheme_storage.create_scheme(1, name="方案 A", scheme_id="a")
    assert not is_annotation_stale(1)

    mark_annotation_stale(1)
    assert is_annotation_stale(1)

    meta = scheme_storage.load_scheme_meta(1, "a")
    assert meta is not None
    assert meta["stale"] is True


def test_clear_annotation_stale_on_confirm(project_dir):
    _seed_floorplan(1)
    mark_annotation_stale(1)
    clear_annotation_stale(1)
    assert not is_annotation_stale(1)


def test_check_design_blocked_when_annotation_stale(project_dir):
    _seed_floorplan(1, confirmed=True)
    mark_annotation_stale(1)
    with pytest.raises(StaleDesignBlocked) as exc:
        check_design_operation_allowed(1)
    assert exc.value.code == "annotation_stale"


def test_check_design_blocked_when_not_confirmed(project_dir):
    _seed_floorplan(1, confirmed=False)
    with pytest.raises(StaleDesignBlocked) as exc:
        check_design_operation_allowed(1)
    assert exc.value.code == "annotation_not_confirmed"
