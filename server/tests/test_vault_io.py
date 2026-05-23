from pathlib import Path

import pytest

from app.services.knowledge.vault_io import VAULT_SUBDIRS, bootstrap_vault, ensure_vault_dirs, sync_templates


@pytest.fixture
def templates_source() -> Path:
    return Path(__file__).resolve().parents[2] / "vault-templates"


def test_ensure_vault_dirs_creates_structure(tmp_path: Path):
    ensure_vault_dirs(tmp_path)

    for relative in VAULT_SUBDIRS:
        assert (tmp_path / relative).is_dir()

    index_state = tmp_path / ".house-diy" / "index_state.json"
    assert index_state.is_file()
    assert '"version"' in index_state.read_text(encoding="utf-8")


def test_sync_templates_copies_markdown(tmp_path: Path, templates_source: Path):
    if not templates_source.is_dir():
        pytest.skip("vault-templates not found")

    copied = sync_templates(tmp_path, templates_source)

    assert len(copied) >= 2
    assert (tmp_path / "Templates" / "case-template.md").is_file()
    assert (tmp_path / "Templates" / "reference-template.md").is_file()


def test_bootstrap_vault(tmp_path: Path, templates_source: Path):
    if not templates_source.is_dir():
        pytest.skip("vault-templates not found")

    result = bootstrap_vault(tmp_path, templates_source)

    assert "Cases" in result["directories"]
    assert "case-template.md" in result["templates"]
    assert "reference-template.md" in result["templates"]
