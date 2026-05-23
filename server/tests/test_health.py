import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_returns_ok_and_services():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "omlx" in body["services"]
    assert "comfyui" in body["services"]
    assert "service_details" in body
    assert body["service_details"]["omlx"]["web_url"].endswith("/admin")


@pytest.mark.asyncio
async def test_service_logs_unknown_service():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/health/logs/unknown")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_service_logs_returns_payload():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/health/logs/vault?tail=20")
    assert resp.status_code == 200
    body = resp.json()
    assert body["service"] == "vault"
    assert "lines" in body
    assert "offset" in body
