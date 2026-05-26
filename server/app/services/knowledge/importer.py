from __future__ import annotations

import base64
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.services.knowledge.indexer import KnowledgeIndexer, _slugify, get_knowledge_indexer
from app.services.knowledge.vault_io import ensure_vault_dirs
from app.services.omlx_client import OmlxClient, get_omlx_client

ALLOWED_IMAGE_SUFFIX = {".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_IMPORT_SUFFIX = ALLOWED_IMAGE_SUFFIX | {".pdf"}


def _reference_prompt(title: str) -> str:
    return (
        f"请用中文总结这张室内设计参考图的风格、配色与家具特点，标题：{title}。"
        "输出 3-5 句话，适合写入 Obsidian 知识库。"
    )


def _summarize_image(
    content: bytes,
    filename: str,
    title: str,
    omlx_client: OmlxClient | None = None,
) -> str:
    client = omlx_client or get_omlx_client()
    suffix = Path(filename).suffix.lower()
    mime = "image/jpeg" if suffix in {".jpg", ".jpeg"} else "image/png"
    encoded = base64.b64encode(content).decode("ascii")
    return client.chat_vision(_reference_prompt(title), encoded, mime_type=mime)


def import_reference(
    content: bytes,
    filename: str,
    title: str | None = None,
    tags: list[str] | None = None,
    vault_root: Path | None = None,
    indexer: KnowledgeIndexer | None = None,
    omlx_client: OmlxClient | None = None,
) -> dict:
    """
    导入外部参考到 Vault References 并建立索引

    @param content 文件二进制
    @param filename 原始文件名
    @param title 标题
    @param tags 标签
    @param vault_root Vault 根路径
    @param indexer 索引器
    @param omlx_client oMLX 客户端
    @return 导入结果
    """
    vault = vault_root or settings.vault_path()
    ensure_vault_dirs(vault)
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_IMPORT_SUFFIX:
        raise ValueError(f"unsupported import type: {suffix}")

    display_title = title or Path(filename).stem
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = _slugify(display_title)
    note_path = vault / "References" / f"{date_str}-{slug}.md"
    asset_name = f"{slug}{suffix}"
    asset_path = vault / "Assets" / asset_name
    asset_path.write_bytes(content)

    if suffix in ALLOWED_IMAGE_SUFFIX:
        summary = _summarize_image(content, filename, display_title, omlx_client=omlx_client)
    else:
        summary = f"PDF 参考文档《{display_title}》，已保存至 Assets/{asset_name}，待人工补充摘要。"

    tag_text = ", ".join(tags or [])
    body = f"""---
type: style_ref
title: "{display_title}"
tags: [{tag_text}]
source: import
created: {datetime.now(timezone.utc).isoformat()}
---

# {display_title}

## 摘要

{summary}

## 附件

![[{asset_name}]]
"""
    note_path.write_text(body, encoding="utf-8")

    service = indexer or get_knowledge_indexer()
    doc_id = service.index_markdown_file(note_path, source="import")
    return {
        "path": str(note_path.relative_to(vault)),
        "title": display_title,
        "indexed": doc_id is not None,
    }
