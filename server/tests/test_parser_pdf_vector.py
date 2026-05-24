"""PDF 矢量 path 提取与 structure 渲染"""

from pathlib import Path

import cv2
import numpy as np
import pytest

from app.services.floorplan.parser_pdf_vector import (
    extract_pdf_text_blocks,
    extract_pdf_vector,
    is_area_label_candidate,
    is_room_name_candidate,
    process_pdf_vector_page,
    render_vector_structure,
    vector_extract_to_meta,
)
from app.services.floorplan.pdf_text_hint import build_pdf_text_hint
from app.services.floorplan.pdf_vector_types import PdfTextBlock, PdfVectorExtract, PdfWallSegment

fitz = pytest.importorskip("fitz")


def create_vector_cad_pdf(path: Path, *, with_labels: bool = False) -> None:
    doc = fitz.open()
    page = doc.new_page(width=400, height=300)
    page.draw_rect(fitz.Rect(40, 40, 360, 260), color=(0, 0, 0), width=2)
    page.draw_line(fitz.Point(200, 40), fitz.Point(200, 260), color=(0, 0, 0), width=2)
    for index in range(15):
        page.draw_line(
            fitz.Point(50 + index * 10, 50),
            fitz.Point(50 + index * 10, 80),
            color=(0, 0, 0),
            width=1,
        )
    if with_labels:
        try:
            page.insert_text(fitz.Point(80, 120), "客厅", fontsize=12, fontname="china-s")
        except Exception:
            page.insert_text(fitz.Point(80, 120), "Living", fontsize=12)
        page.insert_text(fitz.Point(240, 120), "28.8", fontsize=10)
    doc.save(str(path))
    doc.close()


@pytest.fixture
def vector_pdf(tmp_path: Path) -> Path:
    pdf_path = tmp_path / "vector_cad.pdf"
    create_vector_cad_pdf(pdf_path)
    return pdf_path


def test_extract_pdf_vector_finds_wall_segments(vector_pdf: Path):
    doc = fitz.open(str(vector_pdf))
    page = doc[0]
    extract = extract_pdf_vector(page, scale=200 / 72.0)
    doc.close()
    assert len(extract.wall_segments) >= 4


def test_dimension_band_segments_filtered(vector_pdf: Path):
    doc = fitz.open(str(vector_pdf))
    page = doc[0]
    extract = extract_pdf_vector(page, scale=200 / 72.0)
    doc.close()
    short_top = [
        segment
        for segment in extract.wall_segments
        if segment.y1 <= 90 and segment.y2 <= 90 and _segment_length(segment) < 40
    ]
    assert not short_top


def _segment_length(segment: PdfWallSegment) -> float:
    return ((segment.x2 - segment.x1) ** 2 + (segment.y2 - segment.y1) ** 2) ** 0.5


def test_render_vector_structure_non_blank(vector_pdf: Path, tmp_path: Path):
    doc = fitz.open(str(vector_pdf))
    page = doc[0]
    extract = extract_pdf_vector(page, scale=200 / 72.0)
    doc.close()
    output = tmp_path / "structure.png"
    render_vector_structure(extract, output, width_px=800, height_px=600)
    image = cv2.imread(str(output))
    assert image is not None
    assert float(np.var(image)) > 100.0


def test_process_pdf_vector_page_writes_files(vector_pdf: Path, tmp_path: Path):
    doc = fitz.open(str(vector_pdf))
    page = doc[0]
    extract = process_pdf_vector_page(page, tmp_path, width_px=800, height_px=600, scale=200 / 72.0)
    doc.close()
    assert extract is not None
    assert (tmp_path / "source_vector_structure.png").is_file()
    assert (tmp_path / "pdf_vector_meta.json").is_file()


def test_extract_pdf_text_blocks_with_labels(tmp_path: Path):
    pdf_path = tmp_path / "labeled.pdf"
    create_vector_cad_pdf(pdf_path, with_labels=True)
    doc = fitz.open(str(pdf_path))
    blocks = extract_pdf_text_blocks(doc[0])
    doc.close()
    texts = {block.text for block in blocks}
    assert "28.8" in texts
    assert "客厅" in texts or "Living" in texts


def test_room_and_area_candidates():
    assert is_room_name_candidate("客厅")
    assert is_area_label_candidate("28.8")
    assert not is_area_label_candidate("客厅")


def test_build_pdf_text_hint_formats_json():
    blocks = [
        PdfTextBlock(text="客厅", bbox=(0, 0, 10, 10)),
        PdfTextBlock(text="28.8", bbox=(20, 0, 30, 10)),
    ]
    hint = build_pdf_text_hint(blocks)
    assert hint is not None
    assert "客厅" in hint
    assert "仅供参考" in hint


def test_build_pdf_text_hint_empty():
    assert build_pdf_text_hint([]) is None


def test_vector_extract_to_meta():
    extract = PdfVectorExtract(
        wall_segments=[PdfWallSegment(0, 0, 100, 0, 1)],
        text_blocks=[PdfTextBlock("客厅", (0, 0, 1, 1))],
        path_count=20,
    )
    meta = vector_extract_to_meta(extract)
    assert meta["structure_source"] == "vector"
    assert meta["pdf_wall_segments"] == 1
