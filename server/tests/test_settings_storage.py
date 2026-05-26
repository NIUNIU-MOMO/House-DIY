import json

import pytest

from app.services.settings_storage import (
    StorageSettings,
    get_settings_path,
    load_storage_settings,
    resolve_output_root,
    save_storage_settings,
)


@pytest.fixture
def settings_file(tmp_path, monkeypatch):
    path = tmp_path / "settings.local.json"
    monkeypatch.setattr("app.services.settings_storage.get_settings_path", lambda: path)
    return path


def test_load_defaults_when_missing(settings_file):
    assert settings_file.is_file() is False
    settings = load_storage_settings()
    assert settings.output_root == "./data/projects"


def test_save_and_load_storage_settings(settings_file):
    save_storage_settings(StorageSettings(output_root="/tmp/house-diy-output"))
    loaded = load_storage_settings()
    assert loaded.output_root == "/tmp/house-diy-output"
    data = json.loads(settings_file.read_text(encoding="utf-8"))
    assert data["output_root"] == "/tmp/house-diy-output"


def test_resolve_output_root_prefers_file(settings_file, tmp_path, monkeypatch):
    custom = tmp_path / "from-file"
    save_storage_settings(StorageSettings(output_root=str(custom)))
    resolved = resolve_output_root(env_fallback="/tmp/env-fallback")
    assert resolved == custom.resolve()


def test_get_settings_path_is_under_server():
    path = get_settings_path()
    assert path.name == "settings.local.json"
    assert path.parent.name == "server"
