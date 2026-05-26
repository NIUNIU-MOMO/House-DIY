import threading


class ParseTaskCancelled(Exception):
    """用户取消户型解析任务"""


class ParseTaskControl:
    def __init__(self) -> None:
        self._cancelled: set[int] = set()
        self._lock = threading.Lock()

    def register(self, task_id: int) -> None:
        with self._lock:
            self._cancelled.discard(task_id)

    def request_cancel(self, task_id: int) -> None:
        with self._lock:
            self._cancelled.add(task_id)

    def is_cancelled(self, task_id: int) -> bool:
        with self._lock:
            return task_id in self._cancelled

    def clear(self, task_id: int) -> None:
        with self._lock:
            self._cancelled.discard(task_id)

    def ensure_running(self, task_id: int) -> None:
        if self.is_cancelled(task_id):
            raise ParseTaskCancelled()


parse_task_control = ParseTaskControl()
