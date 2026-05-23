import pytest

from app.services.render.storage import RenderRecord, resolve_cover_image_url, upsert_render

MINI_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.floorplan.storage.settings.house_diy_projects_dir",
        str(tmp_path),
    )
    return tmp_path


def test_resolve_cover_image_url_returns_first_render(data_dir):
    project_id = 42
    upsert_render(
        project_id,
        RenderRecord(
            room_id="r1",
            room_name="客厅",
            filename="r1.png",
            prompt="interior design",
        ),
        MINI_PNG,
    )

    assert resolve_cover_image_url(project_id) == f"/api/v1/projects/{project_id}/renders/r1/image"


def test_resolve_cover_image_url_returns_none_without_renders(data_dir):
    assert resolve_cover_image_url(99) is None
