"""
黄金样本集成测试：mock oMLX 分步 VLM + 真实预处理/质检
"""

import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import pytest
from sqlalchemy.orm import sessionmaker

from app.models.project import Project, ProjectStatus
from app.models.task import Task, TaskStatus, TaskType
from app.services.floorplan import storage
from app.services.floorplan.plan_classifier import PlanClassification
from app.services.floorplan.task_parse import create_floorplan_parse_task, run_floorplan_parse_sync


@dataclass
class GoldenSample:
    sample_id: str
    plan_type: str
    has_watermark: bool
    width: int
    height: int
    expected_rooms: int
    step1: dict
    step2_batches: list[dict]


def _write_cad_image(path: Path, width: int, height: int, room_count: int) -> None:
    image = np.full((height, width, 3), 255, dtype=np.uint8)
    if room_count >= 2:
        cv2.rectangle(image, (40, 40), (width - 40, height - 40), (0, 0, 0), 2)
        cv2.line(image, (width // 2, 40), (width // 2, height - 40), (0, 0, 0), 2)
    else:
        cv2.rectangle(image, (40, 40), (width - 40, height - 40), (0, 0, 0), 2)
    cv2.imwrite(str(path), image)


def _write_marketing_image(path: Path, width: int, height: int, with_watermark: bool) -> None:
    image = np.full((height, width, 3), 240, dtype=np.uint8)
    cv2.rectangle(image, (30, 30), (width - 30, height - 30), (30, 30, 30), 2)
    image[:, : width // 2] = (180, 210, 230)
    image[:, width // 2 :] = (170, 220, 180)
    if with_watermark:
        cv2.circle(image, (width // 2, height // 2), 36, (220, 120, 40), -1)
    cv2.imwrite(str(path), image)


def _polygon_rect(x: float, y: float, w: float, h: float) -> list[dict]:
    return [
        {"x": x, "y": y},
        {"x": x + w, "y": y},
        {"x": x + w, "y": y + h},
        {"x": x, "y": y + h},
    ]


GOLDEN_SAMPLES: list[GoldenSample] = [
    GoldenSample(
        sample_id="G-CAD-1",
        plan_type="cad_lineart",
        has_watermark=False,
        width=480,
        height=360,
        expected_rooms=2,
        step1={
            "scale_hint": 100,
            "rooms": [
                {"id": "r1", "name": "客厅", "area_label": "28.8"},
                {"id": "r2", "name": "卧室", "area_label": "15.0"},
            ],
        },
        step2_batches=[
            {
                "rooms": [
                    {"id": "r1", "polygon": _polygon_rect(40, 40, 200, 280)},
                    {"id": "r2", "polygon": _polygon_rect(240, 40, 200, 280)},
                ]
            }
        ],
    ),
    GoldenSample(
        sample_id="G-CAD-2",
        plan_type="cad_lineart",
        has_watermark=False,
        width=520,
        height=380,
        expected_rooms=3,
        step1={
            "scale_hint": 100,
            "rooms": [
                {"id": "r1", "name": "客厅", "area_label": "20.0"},
                {"id": "r2", "name": "主卧", "area_label": "14.0"},
                {"id": "r3", "name": "厨房", "area_label": "6.5"},
            ],
        },
        step2_batches=[
            {
                "rooms": [
                    {"id": "r1", "polygon": _polygon_rect(40, 40, 220, 200)},
                    {"id": "r2", "polygon": _polygon_rect(260, 40, 220, 200)},
                ]
            },
            {"rooms": [{"id": "r3", "polygon": _polygon_rect(40, 240, 180, 100)}]},
        ],
    ),
    GoldenSample(
        sample_id="G-CAD-3",
        plan_type="cad_lineart",
        has_watermark=False,
        width=500,
        height=400,
        expected_rooms=2,
        step1={
            "scale_hint": None,
            "rooms": [
                {"id": "r1", "name": "L型客厅", "area_label": "30.0"},
                {"id": "r2", "name": "卧室", "area_label": "12.0"},
            ],
        },
        step2_batches=[
            {
                "rooms": [
                    {
                        "id": "r1",
                        "polygon": [
                            {"x": 40, "y": 40},
                            {"x": 300, "y": 40},
                            {"x": 300, "y": 180},
                            {"x": 180, "y": 180},
                            {"x": 180, "y": 320},
                            {"x": 40, "y": 320},
                        ],
                    },
                    {"id": "r2", "polygon": _polygon_rect(300, 180, 160, 180)},
                ]
            }
        ],
    ),
    GoldenSample(
        sample_id="G-MKT-1",
        plan_type="marketing_color",
        has_watermark=True,
        width=480,
        height=360,
        expected_rooms=2,
        step1={
            "scale_hint": None,
            "rooms": [
                {"id": "r1", "name": "客厅", "area_label": "25.0"},
                {"id": "r2", "name": "卧室", "area_label": "12.0"},
            ],
        },
        step2_batches=[
            {
                "rooms": [
                    {"id": "r1", "polygon": _polygon_rect(30, 30, 210, 300)},
                    {"id": "r2", "polygon": _polygon_rect(240, 30, 210, 300)},
                ]
            }
        ],
    ),
    GoldenSample(
        sample_id="G-MKT-2",
        plan_type="marketing_color",
        has_watermark=False,
        width=460,
        height=340,
        expected_rooms=2,
        step1={
            "scale_hint": None,
            "rooms": [
                {"id": "r1", "name": "客餐厅", "area_label": "22.0"},
                {"id": "r2", "name": "次卧", "area_label": "10.5"},
            ],
        },
        step2_batches=[
            {
                "rooms": [
                    {"id": "r1", "polygon": _polygon_rect(30, 30, 200, 280)},
                    {"id": "r2", "polygon": _polygon_rect(230, 30, 200, 280)},
                ]
            }
        ],
    ),
    GoldenSample(
        sample_id="G-MKT-3",
        plan_type="marketing_color",
        has_watermark=False,
        width=320,
        height=240,
        expected_rooms=1,
        step1={
            "scale_hint": None,
            "rooms": [{"id": "r1", "name": "开间", "area_label": "18.0"}],
        },
        step2_batches=[{"rooms": [{"id": "r1", "polygon": _polygon_rect(20, 20, 280, 200)}]}],
    ),
]


class GoldenMockOmlxClient:
    def __init__(self, sample: GoldenSample, *, repeat: int = 1):
        responses: list[str] = []
        for _ in range(repeat):
            responses.append(json.dumps(sample.step1, ensure_ascii=False))
            responses.extend(json.dumps(batch, ensure_ascii=False) for batch in sample.step2_batches)
        self.responses = responses
        self.index = 0

    def chat_vision(self, prompt, image_base64, mime_type="image/png", model=None, **kwargs):
        if self.index >= len(self.responses):
            raise RuntimeError("mock oMLX responses exhausted")
        response = self.responses[self.index]
        self.index += 1
        return response


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.floorplan.storage.settings.house_diy_projects_dir",
        str(tmp_path),
    )
    return tmp_path


@pytest.fixture
def patched_task_session(db_session, monkeypatch):
    factory = sessionmaker(bind=db_session.get_bind())
    monkeypatch.setattr("app.services.floorplan.task_parse.SessionLocal", factory)


def _patch_classification(monkeypatch, sample: GoldenSample) -> None:
    def _fake(_source_path: Path) -> PlanClassification:
        return PlanClassification(
            plan_type=sample.plan_type,
            has_watermark=sample.has_watermark,
            saturation_std=25.0 if sample.plan_type == "marketing_color" else 8.0,
            message=f"fixture {sample.sample_id}",
        )

    monkeypatch.setattr("app.services.floorplan.task_parse.classify_floorplan_image", _fake)


def _setup_project_with_sample(
    db_session,
    data_dir: Path,
    sample: GoldenSample,
) -> int:
    project = Project(name=sample.sample_id, status=ProjectStatus.DRAFT)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    project_id = project.id

    project_dir = data_dir / str(project_id)
    project_dir.mkdir(parents=True)
    source_path = project_dir / "source.png"
    if sample.plan_type == "cad_lineart":
        _write_cad_image(source_path, sample.width, sample.height, sample.expected_rooms)
    else:
        _write_marketing_image(source_path, sample.width, sample.height, sample.has_watermark)

    storage.save_upload(project_id, source_path.read_bytes(), "source.png")
    storage.patch_meta(
        project_id,
        {
            "plan_type": sample.plan_type,
            "has_watermark": sample.has_watermark,
            "plan_type_message": f"fixture {sample.sample_id}",
        },
    )
    return project_id


@pytest.mark.parametrize("sample", GOLDEN_SAMPLES, ids=[item.sample_id for item in GOLDEN_SAMPLES])
def test_golden_sample_multistep_parse(sample, data_dir, db_session, patched_task_session, monkeypatch):
    _patch_classification(monkeypatch, sample)
    project_id = _setup_project_with_sample(db_session, data_dir, sample)
    task = create_floorplan_parse_task(db_session, project_id)
    run_floorplan_parse_sync(task.id, omlx_client=GoldenMockOmlxClient(sample))

    db_session.refresh(task)
    assert task.status == TaskStatus.DONE

    model = storage.load_floorplan(project_id)
    assert model is not None
    assert len(model.rooms) == sample.expected_rooms
    assert model.plan_type == sample.plan_type
    assert model.parse_meta is not None
    assert model.parse_meta.vlm_steps is not None
    assert model.parse_meta.vlm_steps >= 1 + len(sample.step2_batches)
    if model.validation is not None:
        assert model.validation.level != "error"


def test_validation_error_triggers_single_retry(data_dir, db_session, patched_task_session, monkeypatch):
    duplicate_polygon = _polygon_rect(0, 0, 200, 200)
    overlap_sample = GoldenSample(
        sample_id="G-RETRY",
        plan_type="cad_lineart",
        has_watermark=False,
        width=400,
        height=300,
        expected_rooms=2,
        step1={
            "scale_hint": 100,
            "rooms": [
                {"id": "r1", "name": "客厅", "area_label": "20.0"},
                {"id": "r2", "name": "卧室", "area_label": "12.0"},
            ],
        },
        step2_batches=[
            {
                "rooms": [
                    {"id": "r1", "polygon": duplicate_polygon},
                    {"id": "r2", "polygon": duplicate_polygon},
                ]
            }
        ],
    )
    fixed_batches = [
        {
            "rooms": [
                {"id": "r1", "polygon": _polygon_rect(0, 0, 200, 200)},
                {"id": "r2", "polygon": _polygon_rect(200, 0, 200, 200)},
            ]
        }
    ]
    _patch_classification(monkeypatch, overlap_sample)

    class RetryMockOmlxClient:
        def __init__(self):
            self.responses = [
                json.dumps(overlap_sample.step1, ensure_ascii=False),
                json.dumps(overlap_sample.step2_batches[0], ensure_ascii=False),
                json.dumps(overlap_sample.step1, ensure_ascii=False),
                json.dumps(fixed_batches[0], ensure_ascii=False),
            ]
            self.index = 0

        def chat_vision(self, prompt, image_base64, mime_type="image/png", model=None, **kwargs):
            response = self.responses[self.index]
            self.index += 1
            return response

    project_id = _setup_project_with_sample(db_session, data_dir, overlap_sample)
    task = create_floorplan_parse_task(db_session, project_id)
    client = RetryMockOmlxClient()
    run_floorplan_parse_sync(task.id, omlx_client=client)

    model = storage.load_floorplan(project_id)
    assert model is not None
    assert model.parse_meta is not None
    assert model.parse_meta.vlm_steps == 4
    assert client.index == 4
    assert model.validation is not None
    assert model.validation.level != "error"
