from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_get_omlx_models():
    with patch(
        "app.api.health.get_omlx_model_config_response",
        new=AsyncMock(
            return_value={
                "llm_model": "house-llm",
                "vlm_model": "house-vlm-pro",
                "vlm_model_cad": "",
                "vlm_model_marketing": "",
                "embed_model": "house-embed",
                "available_models": ["house-llm", "house-vlm-pro", "house-vlm"],
                "omlx_reachable": True,
            }
        ),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/health/omlx-models")
    assert response.status_code == 200
    body = response.json()
    assert body["vlm_model"] == "house-vlm-pro"
    assert "house-vlm-pro" in body["available_models"]


@pytest.mark.asyncio
async def test_put_omlx_models():
    with patch(
        "app.api.health.apply_omlx_model_config",
        return_value={
            "llm_model": "house-llm",
            "vlm_model": "house-vlm",
            "vlm_model_cad": "",
            "vlm_model_marketing": "",
            "embed_model": "house-embed",
        },
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.put(
                "/api/v1/health/omlx-models",
                json={
                    "llm_model": "house-llm",
                    "vlm_model": "house-vlm",
                    "vlm_model_cad": "",
                    "vlm_model_marketing": "",
                    "embed_model": "house-embed",
                },
            )
    assert response.status_code == 200
    assert response.json()["vlm_model"] == "house-vlm"
