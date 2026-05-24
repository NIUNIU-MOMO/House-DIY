from pathlib import Path

from app.core.config import settings

from app.services.redis_probe import read_redis_docker_logs

SERVICE_KEYS = ("omlx", "comfyui", "redis", "vault")

OMLX_LOG_CANDIDATES = (
    "~/.omlx/logs/omlx.log",
    "~/Library/Logs/omlx/omlx.log",
    "/tmp/omlx.log",
)

VAULT_LOG_KEYWORDS = ("vault", "knowledge", "watcher", "chroma", "indexer")


def _expand(path: str) -> Path:
    return Path(path).expanduser()


def resolve_log_path(service: str) -> Path | None:
    """
    解析组件日志文件路径

    @param service 组件标识 omlx/comfyui/vault
    @return 日志文件路径，不存在时返回 None
    """
    if service == "omlx":
        configured = settings.house_diy_omlx_log_path
        if configured:
            path = _expand(configured)
            return path if path.is_file() else None
        for candidate in OMLX_LOG_CANDIDATES:
            path = _expand(candidate)
            if path.is_file():
                return path
        return None

    if service == "comfyui":
        path = _expand(settings.house_diy_comfyui_log_path)
        return path if path.is_file() else None

    if service == "vault":
        configured = settings.house_diy_vault_log_path
        if configured:
            path = _expand(configured)
            return path if path.is_file() else None
        api_log = settings.api_log_path()
        return api_log if api_log.is_file() else None

    return None


def read_log_chunk(
    service: str,
    offset: int = 0,
    max_bytes: int = 65536,
    tail_lines: int = 200,
) -> dict:
    """
    读取日志增量或尾部

    @param service 组件标识
    @param offset 字节偏移（>0 时增量读取）
    @param max_bytes 单次最大读取字节
    @param tail_lines 首次加载时的尾部行数
    @return 日志片段与新的 offset
    """
    if service == "redis":
        if not _redis_container_exists():
            return {
                "service": service,
                "lines": [],
                "offset": 0,
                "exists": False,
                "path": None,
                "message": "Redis 容器未创建，请先启动 Redis",
            }
        lines = read_redis_docker_logs(tail_lines=tail_lines)
        return {
            "service": service,
            "lines": lines,
            "offset": len(lines),
            "exists": True,
            "path": f"docker logs {REDIS_CONTAINER}",
            "message": None,
        }

    path = resolve_log_path(service)
    if path is None:
        return {
            "service": service,
            "lines": [],
            "offset": 0,
            "exists": False,
            "path": None,
            "message": "未找到日志文件，请确认组件已启动并配置了日志路径",
        }

    size = path.stat().st_size
    if offset <= 0:
        return _read_tail(path, service, tail_lines, size)

    if offset > size:
        offset = size

    with path.open("rb") as handle:
        handle.seek(offset)
        data = handle.read(max_bytes)

    new_offset = offset + len(data)
    lines = _decode_lines(data)

    if service == "vault" and settings.house_diy_vault_log_path == "":
        lines = [line for line in lines if _vault_log_match(line)]

    return {
        "service": service,
        "lines": lines,
        "offset": new_offset,
        "exists": True,
        "path": str(path),
        "message": None,
    }


def _decode_lines(data: bytes) -> list[str]:
    if not data:
        return []
    text = data.decode("utf-8", errors="replace")
    return text.splitlines()


def _vault_log_match(line: str) -> bool:
    lowered = line.lower()
    return any(keyword in lowered for keyword in VAULT_LOG_KEYWORDS)


REDIS_CONTAINER = "house-diy-redis"


def _redis_container_exists() -> bool:
    import subprocess

    try:
        result = subprocess.run(
            ["docker", "container", "inspect", REDIS_CONTAINER],
            capture_output=True,
            timeout=5,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def _read_tail(path: Path, service: str, tail_lines: int, size: int) -> dict:
    chunk_size = min(max(size, 1), 512_000)
    with path.open("rb") as handle:
        handle.seek(max(0, size - chunk_size))
        data = handle.read()

    lines = _decode_lines(data)
    if len(lines) > tail_lines:
        lines = lines[-tail_lines:]

    if service == "vault" and settings.house_diy_vault_log_path == "":
        lines = [line for line in lines if _vault_log_match(line)]
        if not lines:
            lines = ["（暂无 Vault 相关日志，索引/导入操作后会出现在 API 日志中）"]

    return {
        "service": service,
        "lines": lines,
        "offset": size,
        "exists": True,
        "path": str(path),
        "message": None,
    }
