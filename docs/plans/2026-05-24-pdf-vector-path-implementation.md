# PDF Vector Path Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extract wall/text vector paths from CAD-export PDFs, render a dedicated structure image for VLM, and optionally inject PDF text as Step1 hints.

**Architecture:** Extend `ensure_raster_source` to detect vector PDFs and call `parser_pdf_vector` for path extraction + rendering. `task_parse` selects `source_vector_structure.png` when `structure_source=vector`. Scan PDFs and PNG uploads remain unchanged.

**Tech Stack:** PyMuPDF (fitz), OpenCV, NumPy, existing VLM pipeline

---

### Task 1: Data types and constants

**Files:**
- Create: `server/app/services/floorplan/pdf_vector_types.py`

**Step 1:** Create dataclasses `PdfWallSegment`, `PdfTextBlock`, `PdfVectorExtract` with constants `MIN_WALL_LENGTH_PT`, `MAX_WALL_WIDTH_PT`, `DIMENSION_BAND_RATIO`.

---

### Task 2: Path extraction and rendering

**Files:**
- Create: `server/app/services/floorplan/parser_pdf_vector.py`
- Test: `server/tests/test_parser_pdf_vector.py`

**APIs:** `extract_pdf_vector`, `extract_pdf_text_blocks`, `render_vector_structure`, `process_pdf_vector_page`

**Step 1:** Failing tests with programmatic PDF fixture (≥4 wall segments, dimension band filtered)

**Step 2:** Implement extraction from `page.get_drawings()` and text from `page.get_text("dict")`

**Step 3:** Render white-bg black-line PNG; assert variance > 0

---

### Task 3: Integrate into ensure_raster_source

**Files:**
- Modify: `server/app/services/floorplan/parser_pdf.py`
- Modify: `server/app/services/floorplan/storage.py`

When `pdf_mode=vector_rasterized`: write `source_vector_structure.png`, `pdf_vector_meta.json`, extend meta with `structure_source`, `pdf_wall_segments`, `pdf_text_blocks`.

---

### Task 4: Pipeline wiring (preprocess / task_parse)

**Files:**
- Modify: `server/app/services/floorplan/task_parse.py`
- Modify: `server/app/services/floorplan/storage.py` — `get_parse_structural_path`

Vector PDF: skip raster preprocess morph; use vector structure directly with zero crop offset.

---

### Task 5: Step1 PDF text hint

**Files:**
- Create: `server/app/services/floorplan/pdf_text_hint.py`
- Modify: `server/app/services/floorplan/parser_vlm.py`
- Modify: `server/app/services/floorplan/task_parse.py`

---

### Task 6: Tests and fixture script

**Files:**
- Create: `scripts/generate-pdf-fixtures.py`
- Expand: `server/tests/test_parser_pdf.py`, `server/tests/test_parser_pdf_vector.py` (≥8 cases)
- Expand: `server/tests/test_floorplan_parse_e2e.py` — vector PDF integration

---

### Task 7: Regression

```bash
cd server && pytest tests/test_parser_pdf.py tests/test_parser_pdf_vector.py tests/test_floorplan_parse_e2e.py -q
```
