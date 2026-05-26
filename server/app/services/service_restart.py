from __future__ import annotations

"""
组件重启：调用 scripts/restart-*.sh
"""

import asyncio
from pathlib import Path

RESTARTABLE_SERVICES = {
    "comfyui": "restart-comfyui.sh",
    "redis": "restart-redis.sh",
    "vault": "restart-vault.sh",
}

RESTART_TIMEOUT_SECONDS = 120.0


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def restart_script_path(service: str) -> Path | None:
    """
    解析组件重启脚本路径

    @param service 组件标识
    @return 脚本绝对路径，不可重启时返回 None
    """
    script_name = RESTARTABLE_SERVICES.get(service)
    if not script_name:
        return None
    path = repo_root() / "scripts" / script_name
    return path if path.is_file() else None


async def restart_service(service: str) -> dict:
    """
    执行组件重启脚本

    @param service 组件标识 comfyui / redis / vault
    @return 执行结果
    """
    script = restart_script_path(service)
    if script is None:
        raise ValueError(f"组件 {service} 不支持重启")

    proc = await asyncio.create_subprocess_exec(
        "bash",
        str(script),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=str(repo_root()),
    )
    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=RESTART_TIMEOUT_SECONDS)
    output = stdout.decode("utf-8", errors="replace").strip()
    success = proc.returncode == 0

    return {
        "service": service,
        "success": success,
        "exit_code": proc.returncode,
        "output": output,
    }
