from __future__ import annotations

"""
户型存储与保存前处理
"""

from app.schemas.floorplan import FloorPlanModel, ParseMeta
from app.services.floorplan.parser_seg import SegRoomRegion
from app.services.floorplan.parser_validate import validate_floorplan
from app.services.floorplan.parser_vlm import walls_from_room_polygons


def sync_walls_from_rooms(model: FloorPlanModel) -> FloorPlanModel:
    """
    用房间 polygon 边生成墙线，保证墙线与房间同源

    @param model 户型模型
    @return 同步墙线后的模型
    """
    if not model.rooms:
        return model
    walls = walls_from_room_polygons([room.polygon for room in model.rooms])
    return model.model_copy(update={"walls": walls})


def prepare_floorplan_for_save(
    model: FloorPlanModel,
    *,
    parse_meta: ParseMeta | None = None,
    low_resolution: bool = False,
    seg_regions: list[SegRoomRegion] | None = None,
) -> FloorPlanModel:
    """
    保存前同步墙线并执行质检

    @param model 户型模型
    @param parse_meta 解析元信息（可选，覆盖 model 内已有值）
    @param low_resolution 源图是否低分辨率
    @param seg_regions segmentation 区域（可选，用于 Seg/VLM 交叉校验）
    @return 可写入磁盘的模型
    """
    synced = sync_walls_from_rooms(model)
    validation = validate_floorplan(
        synced,
        plan_type=synced.plan_type,
        low_resolution=low_resolution,
        seg_regions=seg_regions,
    )
    meta = parse_meta if parse_meta is not None else synced.parse_meta
    if meta is not None and seg_regions is not None:
        seg_warnings = sum(1 for issue in validation.issues if issue.code == "SEG_VLM_MISMATCH")
        meta = meta.model_copy(update={"seg_match_warnings": seg_warnings})
    return synced.model_copy(update={"validation": validation, "parse_meta": meta})
