from __future__ import annotations

from app.services.design import scheme_storage
from app.services.floorplan import storage
from app.schemas.floorplan import FloorPlanStatus


class StaleDesignBlocked(Exception):
    """设计相关操作被 stale 或确认状态拦截"""

    def __init__(self, message: str, code: str = "stale_blocked") -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def is_annotation_stale(project_id: int) -> bool:
    """
    标注是否因重新解析而 stale

    @param project_id 项目 ID
    @return True 表示标注基底已变更
    """
    meta = storage.load_meta(project_id) or {}
    return bool(meta.get("annotation_stale"))


def mark_annotation_stale(project_id: int) -> None:
    """
    重新解析后标记 annotation_stale，并标记全部方案 stale

    @param project_id 项目 ID
    """
    storage.patch_meta(project_id, {"annotation_stale": True})
    scheme_storage.mark_all_schemes_stale(project_id)


def clear_annotation_stale(project_id: int) -> None:
    """
    确认标注后清除 annotation_stale

    @param project_id 项目 ID
    """
    storage.patch_meta(project_id, {"annotation_stale": False})


def check_design_operation_allowed(
    project_id: int,
    scheme_id: str | None = None,
    *,
    require_confirmed: bool = True,
) -> None:
    """
    设计生成/微调前检查 stale 与 confirmed 状态

    @param project_id 项目 ID
    @param scheme_id 方案 ID（可选）
    @param require_confirmed 是否要求标注已确认
    @raises StaleDesignBlocked 不满足条件时抛出
    """
    if is_annotation_stale(project_id):
        raise StaleDesignBlocked(
            "户型已变更，请先保存并确认标注",
            code="annotation_stale",
        )

    if require_confirmed:
        floorplan = storage.load_floorplan(project_id)
        if floorplan is None or floorplan.status != FloorPlanStatus.CONFIRMED:
            raise StaleDesignBlocked(
                "请先确认标注后再进行设计",
                code="annotation_not_confirmed",
            )

    if scheme_id is not None:
        scheme_meta = scheme_storage.load_scheme_meta(project_id, scheme_id)
        if scheme_meta is not None and scheme_meta.get("stale"):
            raise StaleDesignBlocked(
                "方案标注基底已变更，请重新确认标注后再设计",
                code="scheme_stale",
            )
