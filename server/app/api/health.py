import httpx
from fastapi import APIRouter, HTTPException, Query, status

from app.core.config import settings
from app.schemas.omlx_models import OmlxModelConfig, OmlxModelConfigResponse, OmlxModelConfigUpdate
from app.services.omlx_model_config import (
    apply_omlx_model_config,
    get_omlx_model_config_response,
)
from app.services.redis_probe import probe_redis
from app.services.service_logs import SERVICE_KEYS, read_log_chunk
from app.services.service_restart import restart_service

router = APIRouter(prefix="/health", tags=["health"])

SERVICE_LABELS = {
    "omlx": "oMLX",
    "comfyui": "ComfyUI",
    "redis": "Redis",
    "vault": "Vault",
}

RESTARTABLE_SERVICES = frozenset({"comfyui", "redis", "vault"})


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
            "restartable": False,
        },
        "comfyui": {
            "label": SERVICE_LABELS["comfyui"],
            "web_url": settings.comfyui_web_url(),
            "external": True,
            "restartable": True,
        },
        "redis": {
            "label": SERVICE_LABELS["redis"],
            "web_url": "",
            "external": False,
            "restartable": True,
        },
        "vault": {
            "label": SERVICE_LABELS["vault"],
            "web_url": "/knowledge",
            "external": False,
            "restartable": True,
        },
    }


@router.get("")
async def health():
    omlx_status = await _probe(settings.house_diy_omlx_base_url.replace("/v1", ""), "/health")
    comfyui_status = await _probe(settings.house_diy_comfyui_base_url, "/system_stats")
    redis_status = await probe_redis()
    vault_exists = settings.vault_path().is_dir()

    return {
        "status": "ok",
        "services": {
            "omlx": omlx_status,
            "comfyui": comfyui_status,
            "redis": redis_status,
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


@router.get("/omlx-models", response_model=OmlxModelConfigResponse)
async def get_omlx_models():
    """
    读取 oMLX 模型 alias 配置及可用模型列表

    @return 当前配置与 oMLX /v1/models
    """
    return await get_omlx_model_config_response()


@router.put("/omlx-models", response_model=OmlxModelConfig)
async def update_omlx_models(payload: OmlxModelConfigUpdate):
    """
    更新 oMLX 模型 alias 配置并立即生效（写入 .env + 刷新客户端缓存）

    @param payload 新 alias 配置
    @return 应用后的配置
    """
    try:
        return apply_omlx_model_config(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post("/restart/{service}")
async def restart_service_endpoint(service: str):
    """
    重启指定组件（调用 scripts/restart-*.sh）

    @param service 组件标识 comfyui / redis / vault
    @return 脚本执行结果
    """
    if service not in RESTARTABLE_SERVICES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该组件不支持重启")

    try:
        result = await restart_service(service)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="重启超时") from exc

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("output") or f"重启 {service} 失败",
        )

    return result
