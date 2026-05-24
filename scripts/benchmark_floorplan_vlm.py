#!/usr/bin/env python3
"""
户型 VLM 基准测试：对 6 个黄金样本输出对比表。

用法:
  python scripts/benchmark_floorplan_vlm.py --mock
  python scripts/benchmark_floorplan_vlm.py --live
  python scripts/benchmark_floorplan_vlm.py --mock --seg
  python scripts/benchmark_floorplan_vlm.py --mock --seg --seg-hint
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "server"
sys.path.insert(0, str(SERVER))

from app.core.config import settings  # noqa: E402
from app.services.floorplan.floorplan_service import prepare_floorplan_for_save  # noqa: E402
from app.services.floorplan.parser_preprocess import preprocess_floorplan_image  # noqa: E402
from app.services.floorplan.parser_seg import extract_room_regions, seg_backend_label  # noqa: E402
from app.services.floorplan.parser_vlm import merge_vlm_result, run_multistep_vlm_parse  # noqa: E402
from app.services.floorplan.seg_hint import build_seg_hint_payload, format_seg_hint_for_prompt  # noqa: E402
from app.services.omlx_client import get_omlx_client  # noqa: E402
from tests.test_floorplan_parse_e2e import (  # noqa: E402
    GOLDEN_SAMPLES,
    GoldenSample,
    _write_cad_image,
    _write_marketing_image,
)


@dataclass
class BenchmarkRow:
    sample_id: str
    plan_type: str
    vlm_model: str
    room_count: int
    expected_rooms: int
    validation_level: str
    vlm_calls: int
    duration_ms: int
    seg_regions: int
    seg_backend: str
    seg_hint_used: bool
    status: str


class GoldenMockClient:
    def __init__(self, sample: GoldenSample):
        responses: list[str] = [json.dumps(sample.step1, ensure_ascii=False)]
        responses.extend(json.dumps(batch, ensure_ascii=False) for batch in sample.step2_batches)
        self.responses = responses
        self.index = 0
        self.models_used: list[str | None] = []

    def chat_vision(self, prompt, image_base64, mime_type="image/png", model=None, **kwargs):
        self.models_used.append(model)
        response = self.responses[self.index]
        self.index += 1
        return response


def _write_sample_image(sample: GoldenSample, path: Path) -> None:
    if sample.plan_type == "cad_lineart":
        _write_cad_image(path, sample.width, sample.height, sample.expected_rooms)
    else:
        _write_marketing_image(path, sample.width, sample.height, sample.has_watermark)


def _run_sample_mock(sample: GoldenSample, *, with_seg: bool, with_seg_hint: bool) -> BenchmarkRow:
    client = GoldenMockClient(sample)
    vlm_model = settings.vlm_model_for_plan_type(sample.plan_type)
    started = time.perf_counter()
    seg_hint_used = False

    with tempfile.TemporaryDirectory(prefix="house-diy-bench-") as tmp:
        source_path = Path(tmp) / f"{sample.sample_id}.png"
        _write_sample_image(sample, source_path)
        structural_path, _ = preprocess_floorplan_image(
            str(source_path),
            plan_type=sample.plan_type,
            has_watermark=sample.has_watermark,
        )
        image = cv2.imread(structural_path)
        img_h, img_w = image.shape[:2] if image is not None else (sample.height, sample.width)
        mime_type = mimetypes.guess_type(structural_path)[0] or "image/png"
        image_base64 = base64.b64encode(Path(structural_path).read_bytes()).decode("ascii")

        seg_hint_text: str | None = None
        extracted_regions = []
        if with_seg_hint and settings.seg_hint_active():
            extracted_regions = extract_room_regions(structural_path)
            payload = build_seg_hint_payload(extracted_regions)
            seg_hint_text = format_seg_hint_for_prompt(payload) or None
            seg_hint_used = seg_hint_text is not None

        vlm_result, vlm_calls = run_multistep_vlm_parse(
            client,
            image_base64=image_base64,
            mime_type=mime_type,
            img_w=img_w,
            img_h=img_h,
            plan_type=sample.plan_type,
            seg_hint=seg_hint_text,
            vlm_model=vlm_model,
        )
        draft = merge_vlm_result(vlm_result, image_size=(sample.width, sample.height))
        seg_for_validate = extracted_regions if with_seg_hint and settings.house_diy_seg_enabled else None
        prepared = prepare_floorplan_for_save(draft, seg_regions=seg_for_validate)
        seg_regions, seg_backend = (0, "disabled")
        if with_seg:
            if not extracted_regions:
                extracted_regions = extract_room_regions(structural_path)
            seg_regions = len(extracted_regions)
            seg_backend = seg_backend_label()

    duration_ms = int((time.perf_counter() - started) * 1000)
    validation_level = prepared.validation.level if prepared.validation else "unknown"
    return BenchmarkRow(
        sample_id=sample.sample_id,
        plan_type=sample.plan_type,
        vlm_model=vlm_model,
        room_count=len(prepared.rooms),
        expected_rooms=sample.expected_rooms,
        validation_level=validation_level,
        vlm_calls=vlm_calls,
        duration_ms=duration_ms,
        seg_regions=seg_regions,
        seg_backend=seg_backend,
        seg_hint_used=seg_hint_used,
        status="ok",
    )


def _run_sample_live(sample: GoldenSample, *, with_seg: bool, with_seg_hint: bool) -> BenchmarkRow:
    client = get_omlx_client()
    vlm_model = settings.vlm_model_for_plan_type(sample.plan_type)
    started = time.perf_counter()
    status = "ok"
    seg_hint_used = False

    with tempfile.TemporaryDirectory(prefix="house-diy-bench-") as tmp:
        source_path = Path(tmp) / f"{sample.sample_id}.png"
        _write_sample_image(sample, source_path)
        structural_path, _ = preprocess_floorplan_image(
            str(source_path),
            plan_type=sample.plan_type,
            has_watermark=sample.has_watermark,
        )
        image = cv2.imread(structural_path)
        img_h, img_w = image.shape[:2] if image is not None else (sample.height, sample.width)
        mime_type = mimetypes.guess_type(structural_path)[0] or "image/png"
        image_base64 = base64.b64encode(Path(structural_path).read_bytes()).decode("ascii")

        seg_hint_text: str | None = None
        extracted_regions = []
        if with_seg_hint and settings.seg_hint_active():
            extracted_regions = extract_room_regions(structural_path)
            payload = build_seg_hint_payload(extracted_regions)
            seg_hint_text = format_seg_hint_for_prompt(payload) or None
            seg_hint_used = seg_hint_text is not None

        try:
            vlm_result, vlm_calls = run_multistep_vlm_parse(
                client,
                image_base64=image_base64,
                mime_type=mime_type,
                img_w=img_w,
                img_h=img_h,
                plan_type=sample.plan_type,
                seg_hint=seg_hint_text,
                vlm_model=vlm_model,
            )
            draft = merge_vlm_result(vlm_result, image_size=(sample.width, sample.height))
            seg_for_validate = extracted_regions if with_seg_hint and settings.house_diy_seg_enabled else None
            prepared = prepare_floorplan_for_save(draft, seg_regions=seg_for_validate)
            room_count = len(prepared.rooms)
            validation_level = prepared.validation.level if prepared.validation else "unknown"
        except Exception as exc:
            status = f"error: {exc}"
            vlm_calls = 0
            room_count = 0
            validation_level = "error"

        seg_regions, seg_backend = (0, "disabled")
        if with_seg:
            if not extracted_regions:
                extracted_regions = extract_room_regions(structural_path)
            seg_regions = len(extracted_regions)
            seg_backend = seg_backend_label()

    duration_ms = int((time.perf_counter() - started) * 1000)
    return BenchmarkRow(
        sample_id=sample.sample_id,
        plan_type=sample.plan_type,
        vlm_model=vlm_model,
        room_count=room_count,
        expected_rooms=sample.expected_rooms,
        validation_level=validation_level,
        vlm_calls=vlm_calls,
        duration_ms=duration_ms,
        seg_regions=seg_regions,
        seg_backend=seg_backend,
        seg_hint_used=seg_hint_used,
        status=status,
    )


def _print_table(rows: list[BenchmarkRow], *, mode: str) -> None:
    headers = [
        "sample",
        "plan_type",
        "vlm_model",
        "rooms",
        "expect",
        "validation",
        "vlm_calls",
        "ms",
        "seg",
        "seg_backend",
        "seg_hint",
        "status",
    ]
    print(f"\n=== Floorplan VLM Benchmark ({mode}) ===")
    print(
        f"default={settings.house_diy_omlx_vlm_model} "
        f"cad={settings.house_diy_omlx_vlm_model_cad or '-'} "
        f"mkt={settings.house_diy_omlx_vlm_model_marketing or '-'}"
    )
    print("\t".join(headers))
    for row in rows:
        print(
            "\t".join(
                [
                    row.sample_id,
                    row.plan_type,
                    row.vlm_model,
                    str(row.room_count),
                    str(row.expected_rooms),
                    row.validation_level,
                    str(row.vlm_calls),
                    str(row.duration_ms),
                    str(row.seg_regions),
                    row.seg_backend,
                    str(row.seg_hint_used),
                    row.status,
                ]
            )
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark floorplan VLM on golden samples")
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--mock", action="store_true", help="使用 mock oMLX 响应（离线）")
    mode_group.add_argument("--live", action="store_true", help="调用真实 oMLX VLM")
    parser.add_argument("--seg", action="store_true", help="同时跑 segmentation 区域统计")
    parser.add_argument("--seg-hint", action="store_true", help="将 seg 区域注入 VLM Step2 prompt 并做交叉校验")
    args = parser.parse_args()

    if args.seg or args.seg_hint:
        settings.house_diy_seg_enabled = True
    if args.seg_hint:
        settings.house_diy_seg_hint_enabled = True

    rows: list[BenchmarkRow] = []
    for sample in GOLDEN_SAMPLES:
        if args.mock:
            rows.append(_run_sample_mock(sample, with_seg=args.seg or args.seg_hint, with_seg_hint=args.seg_hint))
        else:
            rows.append(_run_sample_live(sample, with_seg=args.seg or args.seg_hint, with_seg_hint=args.seg_hint))

    _print_table(rows, mode="mock" if args.mock else "live")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
