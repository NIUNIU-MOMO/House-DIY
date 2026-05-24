from app.schemas.floorplan import FloorPlanModel, Point, Room, Wall
from app.services.floorplan.floorplan_service import prepare_floorplan_for_save, sync_walls_from_rooms


def test_sync_walls_from_rooms_uses_polygon_edges():
    model = FloorPlanModel(
        rooms=[
            Room(
                id="r1",
                name="客厅",
                polygon=[
                    Point(x=0, y=0),
                    Point(x=100, y=0),
                    Point(x=100, y=80),
                    Point(x=0, y=80),
                ],
            )
        ],
        walls=[Wall(id="cv1", points=[Point(x=999, y=0), Point(x=999, y=50)])],
    )
    synced = sync_walls_from_rooms(model)
    assert synced.walls
    assert synced.walls[0].points[0].x == 0
    assert all(not wall.id.startswith("cv") for wall in synced.walls)


def test_prepare_floorplan_for_save_adds_validation():
    model = FloorPlanModel(
        rooms=[
            Room(
                id="r1",
                name="A",
                polygon=[
                    Point(x=0, y=0),
                    Point(x=10, y=0),
                    Point(x=10, y=10),
                    Point(x=0, y=10),
                ],
            ),
            Room(
                id="r2",
                name="B",
                polygon=[
                    Point(x=0, y=0),
                    Point(x=10, y=0),
                    Point(x=10, y=10),
                    Point(x=0, y=10),
                ],
            ),
        ]
    )
    prepared = prepare_floorplan_for_save(model)
    assert prepared.validation is not None
    assert prepared.validation.level == "error"
