from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_includes_redis():
    with patch("app.api.health.probe_redis", new=AsyncMock(return_value="online")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["services"]["redis"] == "online"
    assert body["service_details"]["redis"]["label"] == "Redis"
    assert body["service_details"]["redis"]["restartable"] is True
    assert body["service_details"]["omlx"]["restartable"] is False


@pytest.mark.asyncio
async def test_restart_service_success():
    with patch(
        "app.api.health.restart_service",
        new=AsyncMock(
            return_value={
                "service": "comfyui",
                "success": True,
                "exit_code": 0,
                "output": "[ComfyUI] 重启完成",
            }
        ),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/health/restart/comfyui")
    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_restart_service_unknown():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/health/restart/omlx")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_restart_service_failure():
    with patch(
        "app.api.health.restart_service",
        new=AsyncMock(
            return_value={
                "service": "redis",
                "success": False,
                "exit_code": 1,
                "output": "docker unavailable",
            }
        ),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/health/restart/redis")
    assert response.status_code == 500
