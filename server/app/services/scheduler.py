import enum

from app.models.task import TaskStatus

MAX_TASK_RETRIES = 2


class TaskEvent(str, enum.Enum):
    START = "start"
    SUCCEED = "succeed"
    FAIL = "fail"


def next_task_status(
    current: TaskStatus,
    event: TaskEvent,
    retry_count: int,
) -> tuple[TaskStatus, int]:
    """
    任务状态机转换

    @param current 当前状态
    @param event 触发事件
    @param retry_count 已重试次数
    @return 新状态与重试次数
    """
    if event == TaskEvent.START:
        if current in {TaskStatus.PENDING, TaskStatus.RUNNING}:
            return TaskStatus.RUNNING, retry_count
        raise ValueError(f"cannot start from {current}")

    if event == TaskEvent.SUCCEED:
        return TaskStatus.DONE, retry_count

    if event == TaskEvent.FAIL:
        if retry_count < MAX_TASK_RETRIES:
            return TaskStatus.PENDING, retry_count + 1
        return TaskStatus.FAILED, retry_count

    raise ValueError(f"unknown event: {event}")
