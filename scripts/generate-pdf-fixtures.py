#!/usr/bin/env python3
"""生成 PDF 矢量测试 fixture"""

from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "server" / "tests" / "fixtures" / "pdfs"


def create_vector_cad_minimal(path: Path) -> None:
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
    try:
        page.insert_text(fitz.Point(80, 120), "客厅", fontsize=12, fontname="china-s")
    except Exception:
        page.insert_text(fitz.Point(80, 120), "Living", fontsize=12)
    page.insert_text(fitz.Point(240, 120), "28.8", fontsize=10)
    doc.save(str(path))
    doc.close()


def main() -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    create_vector_cad_minimal(FIXTURE_DIR / "vector_cad_minimal.pdf")
    print(f"Wrote {FIXTURE_DIR / 'vector_cad_minimal.pdf'}")


if __name__ == "__main__":
    main()
