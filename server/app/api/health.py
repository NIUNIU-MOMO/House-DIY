import httpx
from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(prefix="/health", tags=["health"])


async def _probe(url: str, path: str = "") -> str:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{url.rstrip('/')}{path}")
            return "online" if resp.status_code < 500 else "offline"
    except Exception:
        return "offline"


@router.get("")
async def health():
    omlx_status = await _probe(settings.house_diy_omlx_base_url.replace("/v1", ""), "/health")
    comfyui_status = await _probe(settings.house_diy_comfyui_base_url, "/system_stats")
    vault_exists = settings.vault_path().is_dir()

    return {
        "status": "ok",
        "services": {
            "omlx": omlx_status,
            "comfyui": comfyui_status,
            "vault": "ready" if vault_exists else "missing",
        },
    }
