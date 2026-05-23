import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from app.core.logging import get_logger

JobCallable = Callable[[], Awaitable[Any]]
logger = get_logger(__name__)


class GpuScheduler:
    """全局 GPU 单槽任务队列"""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._queue: asyncio.Queue[JobCallable] = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker())

    async def enqueue(self, job: JobCallable) -> None:
        await self._queue.put(job)

    async def _worker(self) -> None:
        while True:
            job = await self._queue.get()
            async with self._lock:
                try:
                    await job()
                except Exception:
                    logger.exception("GPU 队列任务失败")
            self._queue.task_done()


gpu_scheduler = GpuScheduler()
