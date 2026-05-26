from __future__ import annotations

"""
PDF 矢量文字块 → VLM Step1 hint
"""

import json

from app.services.floorplan.parser_pdf_vector import is_area_label_candidate, is_room_name_candidate
from app.services.floorplan.pdf_vector_types import PdfTextBlock


def build_pdf_text_hint(text_blocks: list[PdfTextBlock]) -> str | None:
    """
    将 PDF 文字块格式化为 Step1 弱 hint

    @param text_blocks PDF 文字块
    @return hint 文本；无有效候选时返回 None
    """
    if not text_blocks:
        return None

    room_names = [block.text for block in text_blocks if is_room_name_candidate(block.text)]
    area_labels = [block.text for block in text_blocks if is_area_label_candidate(block.text)]
    if not room_names and not area_labels:
        return None

    candidates: list[dict[str, str]] = []
    for index, name in enumerate(room_names):
        entry: dict[str, str] = {"name": name}
        if index < len(area_labels):
            entry["area_label"] = area_labels[index]
        candidates.append(entry)

    for index in range(len(room_names), len(area_labels)):
        candidates.append({"name": "", "area_label": area_labels[index]})

    payload = json.dumps(candidates, ensure_ascii=False, indent=2)
    return (
        "以下文字来自 PDF 矢量层（仅供参考，以图像为准）：\n"
        f"{payload}"
    )
