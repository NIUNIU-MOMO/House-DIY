"""
户型存储与保存前处理
"""

from app.schemas.floorplan import FloorPlanModel, ParseMeta
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
) -> FloorPlanModel:
    """
    保存前同步墙线并执行质检

    @param model 户型模型
    @param parse_meta 解析元信息（可选，覆盖 model 内已有值）
    @return 可写入磁盘的模型
    """
    synced = sync_walls_from_rooms(model)
    validation = validate_floorplan(synced)
    meta = parse_meta if parse_meta is not None else synced.parse_meta
    return synced.model_copy(update={"validation": validation, "parse_meta": meta})
