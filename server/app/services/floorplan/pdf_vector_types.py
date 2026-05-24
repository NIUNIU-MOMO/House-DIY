"""
PDF 矢量 path 提取数据类型
"""

from dataclasses import dataclass, field

MIN_WALL_LENGTH_PT = 20.0
MAX_WALL_WIDTH_PT = 3.0
DIMENSION_BAND_RATIO = 0.12
MAX_PATH_SEGMENTS = 500
VECTOR_LINE_WIDTH_PX = 2

VECTOR_STRUCTURAL_FILENAME = "source_vector_structure.png"
PDF_VECTOR_META_FILENAME = "pdf_vector_meta.json"


@dataclass
class PdfWallSegment:
    """PDF 矢量墙线段"""

    x1: float
    y1: float
    x2: float
    y2: float
    width: float


@dataclass
class PdfTextBlock:
    """PDF 文字块"""

    text: str
    bbox: tuple[float, float, float, float]


@dataclass
class PdfVectorExtract:
    """PDF 首页矢量提取结果"""

    wall_segments: list[PdfWallSegment] = field(default_factory=list)
    text_blocks: list[PdfTextBlock] = field(default_factory=list)
    page_width: float = 0.0
    page_height: float = 0.0
    render_scale: float = 1.0
    path_count: int = 0
