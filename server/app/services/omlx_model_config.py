"""
oMLX 模型 alias 运行时配置：读取、更新、持久化 .env、刷新客户端缓存
"""

from pathlib import Path

import httpx

from app.core.config import settings
from app.schemas.omlx_models import OmlxModelConfig, OmlxModelConfigResponse, OmlxModelConfigUpdate
from app.services.omlx_client import get_omlx_client

ENV_KEY_MAP = {
    "llm_model": "HOUSE_DIY_OMLX_LLM_MODEL",
    "vlm_model": "HOUSE_DIY_OMLX_VLM_MODEL",
    "vlm_model_cad": "HOUSE_DIY_OMLX_VLM_MODEL_CAD",
    "vlm_model_marketing": "HOUSE_DIY_OMLX_VLM_MODEL_MARKETING",
    "embed_model": "HOUSE_DIY_OMLX_EMBED_MODEL",
}


def _server_env_path() -> Path:
    return Path(__file__).resolve().parents[2] / ".env"


def get_omlx_model_config() -> OmlxModelConfig:
    """
    读取当前 oMLX 模型 alias 配置

    @return 模型 alias 配置
    """
    return OmlxModelConfig(
        llm_model=settings.house_diy_omlx_llm_model,
        vlm_model=settings.house_diy_omlx_vlm_model,
        vlm_model_cad=settings.house_diy_omlx_vlm_model_cad,
        vlm_model_marketing=settings.house_diy_omlx_vlm_model_marketing,
        embed_model=settings.house_diy_omlx_embed_model,
    )


async def fetch_omlx_available_models() -> tuple[list[str], bool]:
    """
    从 oMLX OpenAI 兼容接口拉取可用模型 id/alias

    @return (模型 id 列表, oMLX 是否可达)
    """
    url = f"{settings.house_diy_omlx_base_url.rstrip('/')}/models"
    headers = {"Authorization": f"Bearer {settings.house_diy_omlx_api_key or 'local'}"}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code >= 400:
                return [], False
            payload = response.json()
            models = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(models, list):
                return [], True
            ids = sorted({str(item.get("id")).strip() for item in models if item.get("id")})
            return ids, True
    except Exception:
        return [], False


async def get_omlx_model_config_response() -> OmlxModelConfigResponse:
    """
    读取配置并附带 oMLX 可用模型列表

    @return 完整配置响应
    """
    config = get_omlx_model_config()
    available, reachable = await fetch_omlx_available_models()
    return OmlxModelConfigResponse(
        **config.model_dump(),
        available_models=available,
        omlx_reachable=reachable,
    )


def _normalize_alias(value: str) -> str:
    return value.strip()


def _validate_aliases(payload: OmlxModelConfigUpdate) -> None:
    required = {
        "llm_model": payload.llm_model,
        "vlm_model": payload.vlm_model,
        "embed_model": payload.embed_model,
    }
    for field_name, value in required.items():
        if not _normalize_alias(value):
            raise ValueError(f"{field_name} 不能为空")


def _persist_env_updates(updates: dict[str, str]) -> None:
    """
    更新 server/.env 中的 HOUSE_DIY_OMLX_* 键

    @param updates env 键 → 值
    """
    env_path = _server_env_path()
    raw_lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.is_file() else []
    updated_keys: set[str] = set()
    new_lines: list[str] = []

    for line in raw_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            new_lines.append(line)
            continue
        key, _, _ = line.partition("=")
        key = key.strip()
        if key in updates:
            new_lines.append(f"{key}={updates[key]}")
            updated_keys.add(key)
        else:
            new_lines.append(line)

    for key, value in updates.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={value}")

    env_path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(new_lines)
    if content and not content.endswith("\n"):
        content += "\n"
    env_path.write_text(content, encoding="utf-8")


def apply_omlx_model_config(payload: OmlxModelConfigUpdate) -> OmlxModelConfig:
    """
    应用模型 alias 配置：内存 settings + .env 持久化 + 清除 oMLX 客户端缓存

    @param payload 新配置
    @return 应用后的配置
    """
    _validate_aliases(payload)

    normalized = OmlxModelConfig(
        llm_model=_normalize_alias(payload.llm_model),
        vlm_model=_normalize_alias(payload.vlm_model),
        vlm_model_cad=_normalize_alias(payload.vlm_model_cad),
        vlm_model_marketing=_normalize_alias(payload.vlm_model_marketing),
        embed_model=_normalize_alias(payload.embed_model),
    )

    settings.house_diy_omlx_llm_model = normalized.llm_model
    settings.house_diy_omlx_vlm_model = normalized.vlm_model
    settings.house_diy_omlx_vlm_model_cad = normalized.vlm_model_cad
    settings.house_diy_omlx_vlm_model_marketing = normalized.vlm_model_marketing
    settings.house_diy_omlx_embed_model = normalized.embed_model

    env_updates = {
        env_key: getattr(normalized, field_name)
        for field_name, env_key in ENV_KEY_MAP.items()
    }
    _persist_env_updates(env_updates)
    get_omlx_client.cache_clear()
    return get_omlx_model_config()
