import pytest


@pytest.mark.asyncio
async def test_get_storage_settings(client, tmp_path, monkeypatch):
    path = tmp_path / "settings.local.json"
    monkeypatch.setattr("app.services.settings_storage.get_settings_path", lambda: path)
    resp = await client.get("/api/v1/settings/storage")
    assert resp.status_code == 200
    body = resp.json()
    assert "output_root" in body
    assert "effective_output_root" in body
    assert "writable" in body


@pytest.mark.asyncio
async def test_put_storage_settings(client, tmp_path, monkeypatch):
    path = tmp_path / "settings.local.json"
    monkeypatch.setattr("app.services.settings_storage.get_settings_path", lambda: path)
    target = tmp_path / "custom-output"
    resp = await client.put(
        "/api/v1/settings/storage",
        json={"output_root": str(target)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["output_root"] == str(target)
    assert body["writable"] is True
    assert path.is_file()
