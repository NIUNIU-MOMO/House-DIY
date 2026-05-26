import json

import pytest

from app.schemas.design_spec import DesignSpec, Render2DSpec, RoomDesignSpec
from app.services.design import scheme_storage
from app.services.design.storage import load_design_spec, save_design_spec
from app.services.floorplan import storage


@pytest.fixture
def project_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.floorplan.storage.settings.house_diy_projects_dir", str(tmp_path))
    monkeypatch.setattr(
        "app.services.settings_storage.resolve_output_root",
        lambda env_fallback=None: tmp_path,
    )
    return tmp_path


def _sample_spec() -> DesignSpec:
    return DesignSpec(
        globalStyle="modern",
        rooms=[
            RoomDesignSpec(
                id="r1",
                name="客厅",
                style="modern",
                render2d=Render2DSpec(prompt="living room"),
            )
        ],
    )


def test_ensure_default_scheme_creates_scheme_a(project_dir):
    scheme = scheme_storage.ensure_default_scheme(1)
    assert scheme.id == "a"
    assert scheme.name == "方案 A"
    assert (project_dir / "1" / "schemes" / "a" / "meta.json").is_file()


def test_create_scheme_respects_limit(project_dir):
    for index in range(scheme_storage.SCHEME_MAX_COUNT):
        scheme_storage.create_scheme(1, name=f"方案 {index}")
    with pytest.raises(ValueError, match="上限"):
        scheme_storage.create_scheme(1, name="超额")


def test_save_and_load_design_spec_under_scheme(project_dir):
    scheme_storage.ensure_default_scheme(1)
    spec = _sample_spec()
    path = save_design_spec(1, spec, scheme_id="a")
    assert path.name == "design_spec.json"
    assert path.parent.name == "a"
    loaded = load_design_spec(1, scheme_id="a")
    assert loaded is not None
    assert loaded.globalStyle == "modern"


def test_delete_scheme_removes_directory(project_dir):
    scheme = scheme_storage.ensure_default_scheme(1)
    scheme_dir = scheme_storage.get_scheme_dir(1, scheme.id)
    assert scheme_dir.is_dir()
    scheme_storage.delete_scheme(1, scheme.id)
    assert not scheme_dir.exists()


def test_mark_all_schemes_stale(project_dir):
    scheme_storage.ensure_default_scheme(1)
    scheme_storage.mark_all_schemes_stale(1)
    meta = json.loads((project_dir / "1" / "schemes" / "a" / "meta.json").read_text(encoding="utf-8"))
    assert meta["stale"] is True
