from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import chromadb

from app.core.config import settings
from app.services.omlx_client import OmlxClient, get_omlx_client

COLLECTION_NAME = "house_diy_knowledge"
INDEX_STATE_VERSION = 1
SCAN_DIRS = ("Cases", "References", "Templates")


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", text.strip().lower())
    return slug.strip("-") or "doc"


def _index_state_path(vault_root: Path) -> Path:
    return vault_root / ".house-diy" / "index_state.json"


def _load_index_state(vault_root: Path) -> dict:
    path = _index_state_path(vault_root)
    if not path.is_file():
        return {"version": INDEX_STATE_VERSION, "documents": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_index_state(vault_root: Path, state: dict) -> None:
    path = _index_state_path(vault_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _infer_doc_type(relative_path: str) -> str:
    if relative_path.startswith("Cases/"):
        return "case"
    if relative_path.startswith("References/"):
        return "ref"
    if relative_path.startswith("Templates/"):
        return "preset"
    return "ref"


def _extract_title(markdown_text: str, fallback: str) -> str:
    for line in markdown_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    match = re.search(r'^project_name:\s*"([^"]+)"', markdown_text, re.MULTILINE)
    if match:
        return match.group(1)
    return fallback


def _extract_index_text(markdown_text: str) -> str:
    body = markdown_text
    if body.startswith("---"):
        parts = body.split("---", 2)
        if len(parts) >= 3:
            body = parts[2]
    return body.strip()[:4000]


class KnowledgeIndexer:
    """Obsidian Vault 向量索引（Chroma + oMLX Embedding）"""

    def __init__(self, vault_root: Path | None = None, omlx_client: OmlxClient | None = None) -> None:
        self.vault_root = vault_root or settings.vault_path()
        self.omlx_client = omlx_client or get_omlx_client()
        chroma_path = self.vault_root / ".house-diy" / "chroma"
        chroma_path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(chroma_path))
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def _embed(self, texts: list[str]) -> list[list[float]]:
        return self.omlx_client.embed(texts)

    def index_document(
        self,
        doc_id: str,
        text: str,
        title: str,
        doc_type: str,
        relative_path: str,
        source: str = "internal",
    ) -> None:
        """
        写入或更新单篇文档索引

        @param doc_id 文档 ID
        @param text 用于 embedding 的正文
        @param title 标题
        @param doc_type 文档类型 case/ref/preset
        @param relative_path Vault 相对路径
        @param source 来源 internal/import
        """
        embedding = self._embed([text])[0]
        metadata = {
            "title": title,
            "type": doc_type,
            "path": relative_path,
            "source": source,
        }
        self._collection.upsert(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata],
        )
        state = _load_index_state(self.vault_root)
        state.setdefault("documents", {})[doc_id] = {
            "title": title,
            "type": doc_type,
            "path": relative_path,
            "source": source,
            "indexed_at": datetime.now(timezone.utc).isoformat(),
        }
        _save_index_state(self.vault_root, state)

    def remove_document(self, doc_id: str) -> None:
        """
        删除文档索引

        @param doc_id 文档 ID
        """
        try:
            self._collection.delete(ids=[doc_id])
        except Exception:
            pass
        state = _load_index_state(self.vault_root)
        documents = state.get("documents", {})
        if doc_id in documents:
            del documents[doc_id]
            _save_index_state(self.vault_root, state)

    def index_markdown_file(self, file_path: Path, source: str = "internal") -> str | None:
        """
        索引单个 Markdown 文件

        @param file_path Markdown 绝对路径
        @param source 来源
        @return 文档 ID
        """
        if not file_path.is_file() or file_path.suffix.lower() != ".md":
            return None
        try:
            relative = str(file_path.relative_to(self.vault_root))
        except ValueError:
            return None

        content = file_path.read_text(encoding="utf-8")
        doc_id = relative
        title = _extract_title(content, file_path.stem)
        doc_type = _infer_doc_type(relative)
        text = _extract_index_text(content)
        if not text:
            return None
        self.index_document(doc_id, text, title, doc_type, relative, source=source)
        return doc_id

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        """
        向量检索 Top-K

        @param query 查询文本
        @param top_k 返回数量
        @return 检索结果列表
        """
        if not query.strip():
            return []
        count = self._collection.count()
        if count == 0:
            return []

        embedding = self._embed([query])[0]
        results = self._collection.query(
            query_embeddings=[embedding],
            n_results=min(top_k, count),
            include=["documents", "metadatas", "distances"],
        )
        items: list[dict] = []
        ids = results.get("ids", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        documents = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]
        for index, doc_id in enumerate(ids):
            metadata = metadatas[index] or {}
            distance = distances[index] if index < len(distances) else 1.0
            score = max(0.0, 1.0 - float(distance))
            snippet = (documents[index] or "")[:120].replace("\n", " ")
            items.append(
                {
                    "id": doc_id,
                    "title": metadata.get("title", doc_id),
                    "score": round(score, 3),
                    "desc": snippet,
                    "type": metadata.get("type", "case"),
                }
            )
        return items

    def list_documents(self) -> list[dict]:
        """
        列出已索引文档

        @return 文档列表
        """
        state = _load_index_state(self.vault_root)
        documents = state.get("documents", {})
        return [
            {
                "id": doc_id,
                "title": meta.get("title", doc_id),
                "type": meta.get("type", "ref"),
                "meta": meta.get("path", doc_id),
                "path": meta.get("path", doc_id),
                "source": meta.get("source", "internal"),
            }
            for doc_id, meta in sorted(documents.items(), key=lambda item: item[1].get("indexed_at", ""), reverse=True)
        ]

    def reindex_all(self) -> tuple[int, int]:
        """
        全量重建 Vault Markdown 索引

        @return (indexed_count, removed_count)
        """
        indexed_ids: set[str] = set()
        indexed_count = 0
        for directory in SCAN_DIRS:
            scan_root = self.vault_root / directory
            if not scan_root.is_dir():
                continue
            for file_path in sorted(scan_root.rglob("*.md")):
                doc_id = self.index_markdown_file(file_path)
                if doc_id:
                    indexed_ids.add(doc_id)
                    indexed_count += 1

        state = _load_index_state(self.vault_root)
        stale_ids = [doc_id for doc_id in state.get("documents", {}) if doc_id not in indexed_ids]
        for doc_id in stale_ids:
            self.remove_document(doc_id)
        return indexed_count, len(stale_ids)


@lru_cache
def get_knowledge_indexer() -> KnowledgeIndexer:
    return KnowledgeIndexer()


def rag_search(query: str, top_k: int = 3, indexer: KnowledgeIndexer | None = None) -> list[dict]:
    """
    RAG 检索入口（无索引时返回空列表）

    @param query 查询
    @param top_k Top-K
    @param indexer 可选 indexer
    @return 结果列表
    """
    service = indexer or get_knowledge_indexer()
    try:
        return service.search(query, top_k=top_k)
    except Exception:
        return []
