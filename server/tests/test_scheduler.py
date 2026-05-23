import pytest

from app.models.task import TaskStatus
from app.services.scheduler import TaskEvent, next_task_status


def test_pending_to_running_to_done():
    status, retries = next_task_status(TaskStatus.PENDING, TaskEvent.START, 0)
    assert status == TaskStatus.RUNNING
    assert retries == 0

    status, retries = next_task_status(status, TaskEvent.SUCCEED, retries)
    assert status == TaskStatus.DONE


def test_fail_retries_then_failed():
    status = TaskStatus.RUNNING
    retries = 0
    for expected_retry in (1, 2):
        status, retries = next_task_status(status, TaskEvent.FAIL, retries)
        assert status == TaskStatus.PENDING
        assert retries == expected_retry

    status, retries = next_task_status(status, TaskEvent.FAIL, retries)
    assert status == TaskStatus.FAILED
    assert retries == 2
