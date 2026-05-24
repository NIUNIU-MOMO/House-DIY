from unittest.mock import patch

import pytest

from app.core.config import settings
from app.schemas.omlx_models import OmlxModelConfigUpdate
from app.services.omlx_client import get_omlx_client
from app.services.omlx_model_config import (
    apply_omlx_model_config,
    get_omlx_model_config,
)


@pytest.fixture(autouse=True)
def reset_client_cache():
    get_omlx_client.cache_clear()
    yield
    get_omlx_client.cache_clear()


@pytest.fixture
def restore_settings():
    snapshot = {
        "llm": settings.house_diy_omlx_llm_model,
        "vlm": settings.house_diy_omlx_vlm_model,
        "cad": settings.house_diy_omlx_vlm_model_cad,
        "mkt": settings.house_diy_omlx_vlm_model_marketing,
        "embed": settings.house_diy_omlx_embed_model,
    }
    yield
    settings.house_diy_omlx_llm_model = snapshot["llm"]
    settings.house_diy_omlx_vlm_model = snapshot["vlm"]
    settings.house_diy_omlx_vlm_model_cad = snapshot["cad"]
    settings.house_diy_omlx_vlm_model_marketing = snapshot["mkt"]
    settings.house_diy_omlx_embed_model = snapshot["embed"]


def test_get_omlx_model_config_reads_settings():
    config = get_omlx_model_config()
    assert config.vlm_model == settings.house_diy_omlx_vlm_model
    assert config.llm_model == settings.house_diy_omlx_llm_model


def test_apply_omlx_model_config_updates_runtime_and_clears_cache(tmp_path, restore_settings, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("HOUSE_DIY_OMLX_VLM_MODEL=house-vlm\n", encoding="utf-8")
    monkeypatch.setattr("app.services.omlx_model_config._server_env_path", lambda: env_file)

    with patch("app.services.omlx_model_config.get_omlx_client") as mock_get:
        mock_get.cache_clear = get_omlx_client.cache_clear
        applied = apply_omlx_model_config(
            OmlxModelConfigUpdate(
                llm_model="house-llm",
                vlm_model="house-vlm-pro",
                vlm_model_cad="",
                vlm_model_marketing="",
                embed_model="house-embed",
            )
        )

    assert applied.vlm_model == "house-vlm-pro"
    assert settings.house_diy_omlx_vlm_model == "house-vlm-pro"
    assert "HOUSE_DIY_OMLX_VLM_MODEL=house-vlm-pro" in env_file.read_text(encoding="utf-8")


def test_apply_rejects_empty_vlm(restore_settings):
    with pytest.raises(ValueError, match="vlm_model"):
        apply_omlx_model_config(
            OmlxModelConfigUpdate(
                llm_model="house-llm",
                vlm_model="  ",
                embed_model="house-embed",
            )
        )
