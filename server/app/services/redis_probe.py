import asyncio
import subprocess

REDIS_CONTAINER = "house-diy-redis"


async def probe_redis() -> str:
    """
    检测 Redis 是否可用（Docker 容器 PONG 或 6379 端口 PONG）

    @return online / offline
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker",
            "exec",
            REDIS_CONTAINER,
            "redis-cli",
            "ping",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3.0)
        if b"PONG" in stdout:
            return "online"
    except Exception:
        pass

    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection("127.0.0.1", 6379), timeout=2.0)
        writer.write(b"PING\r\n")
        await writer.drain()
        data = await asyncio.wait_for(reader.read(64), timeout=2.0)
        writer.close()
        await writer.wait_closed()
        if b"PONG" in data:
            return "online"
    except Exception:
        pass

    return "offline"


def read_redis_docker_logs(tail_lines: int = 200) -> list[str]:
    """
    读取 Redis 容器最近日志

    @param tail_lines 尾部行数
    @return 日志行列表
    """
    try:
        result = subprocess.run(
            ["docker", "logs", "--tail", str(tail_lines), REDIS_CONTAINER],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        combined = (result.stdout or "") + (result.stderr or "")
        lines = [line for line in combined.splitlines() if line.strip()]
        return lines[-tail_lines:] if len(lines) > tail_lines else lines
    except Exception as exc:
        return [f"读取 Redis 日志失败: {exc}"]
