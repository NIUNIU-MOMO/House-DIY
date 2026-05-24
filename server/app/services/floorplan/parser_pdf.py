"""
PDF 户型图解析：矢量检测 + 栅格化，供后续图像链路使用
"""

import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from app.services.floorplan.parser_pdf_vector import process_pdf_vector_page, vector_extract_to_meta

logger = logging.getLogger(__name__)
DEFAULT_PDF_DPI = 200
MIN_SHORT_EDGE_PX = 800
VECTOR_PATH_THRESHOLD = 12


@dataclass
class PdfExtractResult:
    """PDF 提取结果"""

    raster_path: Path
    width: int
    height: int
    pdf_mode: str
    path_count: int
    image_count: int
    low_resolution: bool


def is_pdf_path(source_path: Path | str) -> bool:
    """
    是否为 PDF 文件

    @param source_path 源路径
    @return True 表示 PDF
    """
    return Path(source_path).suffix.lower() == ".pdf"


def _load_fitz():
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("PDF 解析需要 pymupdf，请执行 pip install pymupdf") from exc
    return fitz


def analyze_pdf_vector_content(pdf_path: Path) -> tuple[str, int, int]:
    """
    分析 PDF 首页矢量/扫描特征

    @param pdf_path PDF 路径
    @return (pdf_mode, path_count, image_count)
    """
    fitz = _load_fitz()
    doc = fitz.open(str(pdf_path))
    try:
        if doc.page_count == 0:
            return "scan_rasterized", 0, 0
        page = doc[0]
        drawings = page.get_drawings()
        images = page.get_images(full=True)
        path_count = len(drawings)
        image_count = len(images)
        if path_count >= VECTOR_PATH_THRESHOLD and image_count <= 2:
            return "vector_rasterized", path_count, image_count
        if image_count > 0 and path_count < VECTOR_PATH_THRESHOLD:
            return "scan_rasterized", path_count, image_count
        if path_count >= VECTOR_PATH_THRESHOLD:
            return "vector_rasterized", path_count, image_count
        return "scan_rasterized", path_count, image_count
    finally:
        doc.close()


def rasterize_pdf_first_page(
    pdf_path: Path,
    output_png: Path,
    *,
    dpi: int = DEFAULT_PDF_DPI,
) -> tuple[int, int]:
    """
    将 PDF 首页栅格化为 PNG

    @param pdf_path PDF 路径
    @param output_png 输出 PNG 路径
    @param dpi 渲染 DPI
    @return (宽, 高)
    """
    fitz = _load_fitz()
    doc = fitz.open(str(pdf_path))
    try:
        if doc.page_count == 0:
            raise ValueError("PDF 无页面")
        page = doc[0]
        scale = dpi / 72.0
        matrix = fitz.Matrix(scale, scale)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        output_png.parent.mkdir(parents=True, exist_ok=True)
        pixmap.save(str(output_png))
        return pixmap.width, pixmap.height
    finally:
        doc.close()


def ensure_raster_source(
    source_path: Path,
    *,
    raster_filename: str = "source.png",
    dpi: int = DEFAULT_PDF_DPI,
) -> tuple[Path, dict]:
    """
    确保存在可供 OpenCV / 分类 / VLM 使用的 raster 图像

    @param source_path 上传源文件（PNG/JPG/PDF）
    @param raster_filename 栅格输出文件名（相对源目录）
    @param dpi PDF 渲染 DPI
    @return (raster 路径, 元信息)
    """
    if not is_pdf_path(source_path):
        image = cv2.imread(str(source_path))
        width = image.shape[1] if image is not None else 0
        height = image.shape[0] if image is not None else 0
        short_edge = min(width, height) if width and height else 0
        return source_path, {
            "pdf_mode": None,
            "original_pdf": None,
            "raster_image": source_path.name,
            "low_resolution": short_edge > 0 and short_edge < MIN_SHORT_EDGE_PX,
        }

    raster_path = source_path.parent / raster_filename
    pdf_mode, path_count, image_count = analyze_pdf_vector_content(source_path)
    width, height = rasterize_pdf_first_page(source_path, raster_path, dpi=dpi)
    short_edge = min(width, height)
    meta = {
        "pdf_mode": pdf_mode,
        "original_pdf": source_path.name,
        "raster_image": raster_filename,
        "pdf_path_count": path_count,
        "pdf_image_count": image_count,
        "low_resolution": short_edge < MIN_SHORT_EDGE_PX,
        "structure_source": "raster",
    }

    if pdf_mode == "vector_rasterized":
        fitz = _load_fitz()
        doc = fitz.open(str(source_path))
        try:
            if doc.page_count > 1:
                meta["pdf_multi_page_warning"] = True
            page = doc[0]
            scale = dpi / 72.0
            extract = process_pdf_vector_page(
                page,
                source_path.parent,
                width_px=width,
                height_px=height,
                scale=scale,
            )
            if extract is not None:
                meta.update(vector_extract_to_meta(extract))
        finally:
            doc.close()

    logger.info(
        "PDF 栅格化完成 mode=%s size=%sx%s path=%s",
        pdf_mode,
        width,
        height,
        raster_path,
    )
    return raster_path, meta


def extract_pdf_for_floorplan(
    pdf_path: Path,
    output_dir: Path,
    *,
    dpi: int = DEFAULT_PDF_DPI,
) -> PdfExtractResult:
    """
    PDF 提取入口：矢量分析 + 栅格化

    @param pdf_path PDF 路径
    @param output_dir 输出目录
    @param dpi 渲染 DPI
    @return 提取结果
    """
    output_png = output_dir / "source.png"
    raster_path, meta = ensure_raster_source(pdf_path, raster_filename="source.png", dpi=dpi)
    image = cv2.imread(str(raster_path))
    width = image.shape[1] if image is not None else 0
    height = image.shape[0] if image is not None else 0
    short_edge = min(width, height) if width and height else 0
    return PdfExtractResult(
        raster_path=raster_path,
        width=width,
        height=height,
        pdf_mode=str(meta.get("pdf_mode") or "scan_rasterized"),
        path_count=int(meta.get("pdf_path_count") or 0),
        image_count=int(meta.get("pdf_image_count") or 0),
        low_resolution=short_edge > 0 and short_edge < MIN_SHORT_EDGE_PX,
    )
