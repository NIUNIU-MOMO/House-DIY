from __future__ import annotations

import json
import math
from pathlib import Path

import trimesh

from app.schemas.design_spec import DesignSpec, FurniturePlacement, RoomDesignSpec
from app.schemas.floorplan import FloorPlanModel, OpeningType, Point, Room, Wall
from app.schemas.scene import (
    Bounds3D,
    CollisionBox,
    SceneFurnitureItem,
    ScenePackage,
    ScenePortal,
    SceneRoomMeta,
    Vec3,
)

DEFAULT_SCALE = 100.0
DEFAULT_WALL_HEIGHT = 2.8
DEFAULT_WALL_THICKNESS = 0.2
FLOOR_THICKNESS = 0.05

FLOOR_COLOR = "#C9B896"
WALL_COLOR = "#F0EBE3"
CATEGORY_COLORS: dict[str, str] = {
    "sofa": "#5B7E57",
    "bed": "#5E7FA3",
    "table": "#A07240",
    "chair": "#7A6538",
    "cabinet": "#8A8278",
    "kitchen": "#B8B8B8",
    "bathroom": "#7EB0C4",
    "lighting": "#D9B44A",
    "decor": "#6E9470",
    "storage": "#968878",
    "rug": "#9A6B4F",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def catalog_path() -> Path:
    return repo_root() / "assets" / "furniture" / "catalog.json"


def assets_root() -> Path:
    return repo_root() / "assets"


def _resolve_glb_path(catalog_item: dict) -> Path | None:
    glb_rel = catalog_item.get("glb_path")
    if not glb_rel:
        return None
    candidates = [
        assets_root() / glb_rel,
        assets_root() / "furniture" / Path(glb_rel).name,
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def _infer_room_category(room_name: str) -> str:
    name = room_name or ""
    if any(key in name for key in ("客厅", "起居室")):
        return "living"
    if "餐厅" in name:
        return "dining"
    if "厨房" in name:
        return "kitchen"
    if any(key in name for key in ("主卧", "卧室")):
        return "bedroom"
    if "儿童房" in name:
        return "kids"
    if any(key in name for key in ("长辈", "老人")):
        return "elder"
    if "客房" in name:
        return "guest"
    if any(key in name for key in ("卫生间", "卫浴", "厕所")):
        return "bathroom"
    if "阳台" in name:
        return "balcony"
    return "generic"


def default_furniture_for_room(room_name: str) -> list[FurniturePlacement]:
    """
    DesignSpec 未填家具时，按房间类型补默认摆放

    @param room_name 房间名称
    @return 家具 placement 列表
    """
    category = _infer_room_category(room_name)
    presets: dict[str, list[FurniturePlacement]] = {
        "living": [
            FurniturePlacement(sku="sofa_3seat_modern_01", wall="south", offset=[0.6, 0.35]),
            FurniturePlacement(sku="coffee_table_low_01", wall="south", offset=[2.2, 1.0]),
            FurniturePlacement(sku="tv_stand_01", wall="north", offset=[0.8, 0.25]),
            FurniturePlacement(sku="floor_lamp_01", wall="east", offset=[0.5, 0.35]),
        ],
        "dining": [
            FurniturePlacement(sku="dining_table_rect_4_01", wall="south", offset=[0.4, 1.0]),
            FurniturePlacement(sku="dining_chair_01", wall="south", offset=[0.2, 0.25]),
            FurniturePlacement(sku="dining_chair_01", wall="south", offset=[1.0, 0.25]),
            FurniturePlacement(sku="sideboard_01", wall="north", offset=[0.3, 0.25]),
        ],
        "kitchen": [
            FurniturePlacement(sku="kitchen_cabinet_base_01", wall="south", offset=[0.3, 0.2]),
            FurniturePlacement(sku="kitchen_island_01", wall="south", offset=[1.6, 1.0]),
            FurniturePlacement(sku="kitchen_fridge_v42", wall="west", offset=[0.4, 0.25]),
        ],
        "bedroom": [
            FurniturePlacement(sku="bed_queen_modern_01", wall="north", offset=[0.5, 0.35]),
            FurniturePlacement(sku="nightstand_01", wall="north", offset=[0.15, 0.25]),
            FurniturePlacement(sku="wardrobe_slide_01", wall="west", offset=[0.3, 0.25]),
        ],
        "kids": [
            FurniturePlacement(sku="bed_single_v05", wall="north", offset=[0.4, 0.35]),
            FurniturePlacement(sku="desk_kids_v29", wall="south", offset=[0.3, 0.35]),
            FurniturePlacement(sku="bookshelf_tall_01", wall="east", offset=[0.3, 0.25]),
        ],
        "elder": [
            FurniturePlacement(sku="bed_queen_modern_01", wall="north", offset=[0.5, 0.35]),
            FurniturePlacement(sku="nightstand_01", wall="north", offset=[0.15, 0.25]),
            FurniturePlacement(sku="chair_lounge_v11", wall="south", offset=[0.4, 0.8]),
        ],
        "guest": [
            FurniturePlacement(sku="bed_queen_modern_01", wall="north", offset=[0.5, 0.35]),
            FurniturePlacement(sku="wardrobe_slide_01", wall="west", offset=[0.3, 0.25]),
        ],
        "bathroom": [
            FurniturePlacement(sku="toilet_standard_01", wall="west", offset=[0.2, 0.25]),
            FurniturePlacement(sku="bathroom_basin_v47", wall="south", offset=[0.5, 0.25]),
            FurniturePlacement(sku="shower_enclosure_01", wall="east", offset=[0.3, 0.25]),
        ],
        "balcony": [
            FurniturePlacement(sku="decor_plant_v36", wall="south", offset=[0.4, 0.5]),
            FurniturePlacement(sku="chair_lounge_v12", wall="north", offset=[0.5, 0.6]),
        ],
        "generic": [
            FurniturePlacement(sku="sofa_2seat_compact_01", wall="south", offset=[0.5, 0.35]),
            FurniturePlacement(sku="coffee_table_low_01", wall="south", offset=[1.8, 1.0]),
        ],
    }
    return presets.get(category, presets["generic"])


def _load_furniture_glb(catalog_item: dict) -> trimesh.Trimesh | None:
    path = _resolve_glb_path(catalog_item)
    if path is None:
        return None
    loaded = trimesh.load(str(path), force="mesh")
    if isinstance(loaded, trimesh.Scene):
        geoms = [geom for geom in loaded.geometry.values() if isinstance(geom, trimesh.Trimesh)]
        if not geoms:
            return None
        loaded = trimesh.util.concatenate(geoms)
    if not isinstance(loaded, trimesh.Trimesh) or loaded.vertices.size == 0:
        return None

    target = [catalog_item["width"], catalog_item["depth"], catalog_item["height"]]
    bounds = loaded.bounds
    size = bounds[1] - bounds[0]
    scale_factors = [
        target[index] / size[index] if size[index] > 1e-6 else 1.0
        for index in range(3)
    ]
    loaded.apply_scale(scale_factors)
    bounds = loaded.bounds
    center_x = (bounds[0][0] + bounds[1][0]) / 2
    center_y = (bounds[0][1] + bounds[1][1]) / 2
    loaded.apply_translation([-center_x, -center_y, -bounds[0][2]])
    return loaded


def _apply_furniture_color(mesh: trimesh.Trimesh, hex_color: str) -> trimesh.Trimesh:
    rgb = [int(hex_color[index:index + 2], 16) for index in (1, 3, 5)]
    mesh.visual.vertex_colors = [rgb + [255]] * len(mesh.vertices)
    return mesh


def load_furniture_catalog() -> dict[str, dict]:
    """
    加载家具 catalog

    @return sku -> 条目 dict
    """
    data = json.loads(catalog_path().read_text(encoding="utf-8"))
    return {item["sku"]: item for item in data["items"]}


def _pixels_to_meters(point: Point, scale: float) -> tuple[float, float]:
    return point.x / scale, point.y / scale


def _room_polygon_meters(room: Room, scale: float) -> list[tuple[float, float]]:
    return [_pixels_to_meters(point, scale) for point in room.polygon]


def _room_bounds(polygon_m: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    xs = [point[0] for point in polygon_m]
    ys = [point[1] for point in polygon_m]
    return min(xs), min(ys), max(xs), max(ys)


def _transform_wall_segment(
    start: tuple[float, float],
    end: tuple[float, float],
    height: float,
    thickness: float,
) -> trimesh.Trimesh | None:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    if length < 1e-6:
        return None

    box = trimesh.creation.box(extents=[length, thickness, height])
    angle = math.atan2(dy, dx)
    rotation = trimesh.transformations.rotation_matrix(angle, [0, 0, 1])
    center_x = (start[0] + end[0]) / 2
    center_y = (start[1] + end[1]) / 2
    translation = trimesh.transformations.translation_matrix([center_x, center_y, height / 2])
    box.apply_transform(translation @ rotation)
    return _apply_furniture_color(box, WALL_COLOR)


def _build_floor_mesh(polygon_m: list[tuple[float, float]]) -> trimesh.Trimesh:
    min_x, min_y, max_x, max_y = _room_bounds(polygon_m)
    width = max(max_x - min_x, 1e-3)
    depth = max(max_y - min_y, 1e-3)
    floor = trimesh.creation.box(extents=[width, depth, FLOOR_THICKNESS])
    floor.apply_translation([(min_x + max_x) / 2, (min_y + max_y) / 2, -FLOOR_THICKNESS / 2])
    return _apply_furniture_color(floor, FLOOR_COLOR)


def _build_room_walls(
    polygon_m: list[tuple[float, float]],
    height: float,
    thickness: float,
) -> tuple[list[trimesh.Trimesh], list[CollisionBox]]:
    meshes: list[trimesh.Trimesh] = []
    collision_boxes: list[CollisionBox] = []
    count = len(polygon_m)
    for index in range(count):
        start = polygon_m[index]
        end = polygon_m[(index + 1) % count]
        wall = _transform_wall_segment(start, end, height, thickness)
        if wall is None:
            continue
        meshes.append(wall)
        bounds = wall.bounds
        collision_boxes.append(
            CollisionBox(
                min=[float(bounds[0][0]), float(bounds[0][1]), float(bounds[0][2])],
                max=[float(bounds[1][0]), float(bounds[1][1]), float(bounds[1][2])],
            )
        )
    return meshes, collision_boxes


def _furniture_position(
    bounds: tuple[float, float, float, float],
    placement: FurniturePlacement,
    catalog_item: dict,
) -> tuple[float, float, float]:
    min_x, min_y, max_x, max_y = bounds
    along, inset = placement.offset[0], placement.offset[1]
    width = catalog_item["width"]
    depth = catalog_item["depth"]
    height = catalog_item["height"]

    wall = placement.wall.lower()
    if wall == "south":
        x = min_x + along + width / 2
        y = min_y + inset + depth / 2
    elif wall == "north":
        x = min_x + along + width / 2
        y = max_y - inset - depth / 2
    elif wall == "west":
        x = min_x + inset + depth / 2
        y = min_y + along + width / 2
    elif wall == "east":
        x = max_x - inset - depth / 2
        y = min_y + along + width / 2
    else:
        x = min_x + along + width / 2
        y = min_y + inset + depth / 2

    return x, y, height / 2


def _build_furniture_mesh(
    placement: FurniturePlacement,
    catalog_item: dict,
    position: tuple[float, float, float],
) -> trimesh.Trimesh:
    width = catalog_item["width"]
    depth = catalog_item["depth"]
    height = catalog_item["height"]
    mesh = _load_furniture_glb(catalog_item)
    category = catalog_item.get("category", "table")
    color = CATEGORY_COLORS.get(category, "#8B7355")
    floor_z = 0.0
    if mesh is not None:
        mesh = _apply_furniture_color(mesh.copy(), color)
        mesh.apply_translation([position[0], position[1], floor_z])
        pivot = [position[0], position[1], floor_z]
    else:
        mesh = trimesh.creation.box(extents=[width, depth, height])
        mesh = _apply_furniture_color(mesh, color)
        mesh.apply_translation([position[0], position[1], position[2]])
        pivot = [position[0], position[1], position[2]]
    if placement.rotation:
        rotation = trimesh.transformations.rotation_matrix(
            math.radians(placement.rotation),
            [0, 0, 1],
            point=pivot,
        )
        mesh.apply_transform(rotation)
    return mesh


def _resolve_room_spec(room: Room, spec: DesignSpec) -> RoomDesignSpec | None:
    return next((item for item in spec.rooms if item.id == room.id), None)


def _wall_endpoints_meters(wall: Wall, scale: float) -> tuple[tuple[float, float], tuple[float, float]]:
    return _pixels_to_meters(wall.points[0], scale), _pixels_to_meters(wall.points[1], scale)


def _door_center_meters(opening, wall: Wall, scale: float) -> tuple[float, float]:
    start, end = _wall_endpoints_meters(wall, scale)
    ratio = opening.position
    return start[0] + (end[0] - start[0]) * ratio, start[1] + (end[1] - start[1]) * ratio


def _portal_trigger_box(center_x: float, center_y: float, width: float, height: float = 2.0) -> CollisionBox:
    half = max(width / 2, 0.4)
    depth = 0.5
    return CollisionBox(
        min=[center_x - half, center_y - depth / 2, 0.0],
        max=[center_x + half, center_y + depth / 2, height],
    )


def _room_spawn_point(room: Room, scale: float) -> list[float]:
    polygon_m = _room_polygon_meters(room, scale)
    min_x, min_y, max_x, max_y = _room_bounds(polygon_m)
    return [(min_x + max_x) / 2, (min_y + max_y) / 2, 1.6]


def build_portals(floorplan: FloorPlanModel, scale: float) -> list[ScenePortal]:
    """
    从门洞 openings 生成 Portal 元数据

    @param floorplan 户型模型
    @param scale 像素/米
    @return Portal 列表
    """
    wall_map = {wall.id: wall for wall in floorplan.walls}
    room_map = {room.id: room for room in floorplan.rooms}
    portals: list[ScenePortal] = []

    for opening in floorplan.openings:
        if opening.type != OpeningType.DOOR:
            continue
        if len(opening.connects) < 2:
            continue
        wall = wall_map.get(opening.wall_id)
        if wall is None:
            continue

        door_width_m = opening.width / scale if opening.width > 1 else opening.width
        center_x, center_y = _door_center_meters(opening, wall, scale)
        trigger = _portal_trigger_box(center_x, center_y, door_width_m)

        for source_id in opening.connects:
            source_room = room_map.get(source_id)
            if source_room is None:
                continue
            for target_id in opening.connects:
                if target_id == source_id:
                    continue
                target_room = room_map.get(target_id)
                if target_room is None:
                    continue
                portals.append(
                    ScenePortal(
                        id=f"{opening.id}_{source_id}_to_{target_id}",
                        source_room_id=source_id,
                        target_room_id=target_id,
                        target_room_name=target_room.name,
                        trigger=trigger,
                        spawn=_room_spawn_point(target_room, scale),
                    )
                )
    return portals


def _portals_for_room(room_id: str, portals: list[ScenePortal]) -> list[ScenePortal]:
    return [portal for portal in portals if portal.source_room_id == room_id]


def build_room_scene(
    floorplan: FloorPlanModel,
    room: Room,
    room_spec: RoomDesignSpec | None,
    catalog: dict[str, dict],
    scale: float,
    portals: list[ScenePortal] | None = None,
) -> tuple[list[trimesh.Trimesh], SceneRoomMeta]:
    """
    构建单房间网格与元数据

    @param floorplan 户型模型
    @param room 房间
    @param room_spec 房间 DesignSpec
    @param catalog 家具 catalog
    @param scale 像素/米
    @return (meshes, room_meta)
    """
    polygon_m = _room_polygon_meters(room, scale)
    bounds_tuple = _room_bounds(polygon_m)
    height = room_spec.render3d.ceilingHeight if room_spec else DEFAULT_WALL_HEIGHT

    meshes: list[trimesh.Trimesh] = []
    floor = _build_floor_mesh(polygon_m)
    meshes.append(floor)

    wall_meshes, collision_boxes = _build_room_walls(polygon_m, height, DEFAULT_WALL_THICKNESS)
    meshes.extend(wall_meshes)

    furniture_meta: list[SceneFurnitureItem] = []
    placements: list[FurniturePlacement] = []
    if room_spec:
        placements = list(room_spec.furniture)
        if not placements:
            placements = default_furniture_for_room(room.name)
        for placement in placements:
            catalog_item = catalog.get(placement.sku)
            if catalog_item is None:
                continue
            position = _furniture_position(bounds_tuple, placement, catalog_item)
            mesh = _build_furniture_mesh(placement, catalog_item, position)
            meshes.append(mesh)
            furniture_meta.append(
                SceneFurnitureItem(
                    sku=placement.sku,
                    name=catalog_item["name"],
                    position=[position[0], position[1], position[2]],
                    rotation=placement.rotation,
                    size=[catalog_item["width"], catalog_item["depth"], catalog_item["height"]],
                )
            )

    min_x, min_y, max_x, max_y = bounds_tuple
    room_meta = SceneRoomMeta(
        id=room.id,
        name=room.name,
        bounds=Bounds3D(
            min=Vec3(x=min_x, y=min_y, z=0.0),
            max=Vec3(x=max_x, y=max_y, z=height),
        ),
        collision_boxes=collision_boxes,
        furniture=furniture_meta,
        portals=_portals_for_room(room.id, portals or []),
    )
    return meshes, room_meta


def build_scene(
    floorplan: FloorPlanModel,
    spec: DesignSpec,
    output_dir: Path,
) -> ScenePackage:
    """
    从 confirmed 户型与 DesignSpec 构建 3D 场景包

    @param floorplan 户型模型
    @param spec DesignSpec
    @param output_dir 输出目录
    @return ScenePackage 元数据
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    scale = floorplan.scale or DEFAULT_SCALE
    catalog = load_furniture_catalog()
    all_portals = build_portals(floorplan, scale)

    all_meshes: list[trimesh.Trimesh] = []
    room_metas: list[SceneRoomMeta] = []

    for room in floorplan.rooms:
        room_spec = _resolve_room_spec(room, spec)
        meshes, room_meta = build_room_scene(floorplan, room, room_spec, catalog, scale, all_portals)
        all_meshes.extend(meshes)
        room_metas.append(room_meta)

    if not all_meshes:
        raise ValueError("no room geometry to export")

    export_scene = trimesh.Scene()
    for index, mesh in enumerate(all_meshes):
        export_scene.add_geometry(mesh, node_name=f"part_{index}")
    glb_path = output_dir / "scene.glb"
    export_scene.export(str(glb_path))

    package = ScenePackage(
        version=1,
        gltf="scene.glb",
        status="ready",
        rooms=room_metas,
        portals=all_portals,
        active_room=room_metas[0].id if room_metas else None,
    )
    json_path = output_dir / "scene.json"
    json_path.write_text(package.model_dump_json(indent=2), encoding="utf-8")
    return package


def load_scene_package(project_id: int) -> ScenePackage | None:
    """
    加载项目 scene.json

    @param project_id 项目 ID
    @return ScenePackage 或 None
    """
    from app.services.floorplan.storage import get_project_dir

    path = get_project_dir(project_id) / "scene.json"
    if not path.is_file():
        return None
    return ScenePackage.model_validate(json.loads(path.read_text(encoding="utf-8")))


def get_scene_gltf_path(project_id: int) -> Path | None:
    """
    获取 3D 场景模型路径（优先 GLB 单文件，兼容旧版 glTF+bin）

    @param project_id 项目 ID
    @return 模型文件路径
    """
    from app.services.floorplan.storage import get_project_dir

    project_dir = get_project_dir(project_id)
    glb_path = project_dir / "scene.glb"
    if glb_path.is_file():
        return glb_path
    gltf_path = project_dir / "scene.gltf"
    return gltf_path if gltf_path.is_file() else None


def get_scene_asset_path(project_id: int, filename: str) -> Path | None:
    """
    获取场景附属资源路径（旧版 glTF 外部 buffer 等）

    @param project_id 项目 ID
    @param filename 文件名
    @return 文件路径或 None
    """
    from app.services.floorplan.storage import get_project_dir

    if filename != Path(filename).name or ".." in filename:
        return None
    allowed_prefixes = ("gltf_buffer_", "scene.")
    if not any(filename.startswith(prefix) for prefix in allowed_prefixes):
        return None
    path = get_project_dir(project_id) / filename
    return path if path.is_file() else None
