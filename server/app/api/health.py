import httpx
from fastapi import APIRouter, HTTPException, Query, status

from app.core.config import settings
from app.services.service_logs import SERVICE_KEYS, read_log_chunk

router = APIRouter(prefix="/health", tags=["health"])

SERVICE_LABELS = {
    "omlx": "oMLX",
    "comfyui": "ComfyUI",
    "vault": "Vault",
}


async def _probe(url: str, path: str = "") -> str:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{url.rstrip('/')}{path}")
            return "online" if resp.status_code < 500 else "offline"
    except Exception:
        return "offline"


def _service_details() -> dict[str, dict]:
    return {
        "omlx": {
            "label": SERVICE_LABELS["omlx"],
            "web_url": settings.omlx_admin_url(),
            "external": True,
        },
        "comfyui": {
            "label": SERVICE_LABELS["comfyui"],
            "web_url": settings.comfyui_web_url(),
            "external": True,
        },
        "vault": {
            "label": SERVICE_LABELS["vault"],
            "web_url": "/knowledge",
            "external": False,
        },
    }


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
        "service_details": _service_details(),
    }


@router.get("/logs/{service}")
def service_logs(
    service: str,
    offset: int = Query(default=0, ge=0),
    tail: int = Query(default=200, ge=1, le=1000),
):
    """
    读取组件运行日志（支持 offset 增量拉取）

    @param service 组件标识
    @param offset 字节偏移
    @param tail 首次加载尾部行数
    @return 日志行与新的 offset
    """
    if service not in SERVICE_KEYS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown service")

    return read_log_chunk(service, offset=offset, tail_lines=tail)
