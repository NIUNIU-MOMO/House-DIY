from __future__ import annotations

from fastapi import APIRouter, File, Form, Query, UploadFile, status

from app.schemas.knowledge import (
    KnowledgeDocument,
    KnowledgeImportResponse,
    KnowledgeListResponse,
    KnowledgeReindexResponse,
    KnowledgeSearchResponse,
    KnowledgeSearchResult,
)
from app.services.knowledge.importer import import_reference
from app.services.knowledge.indexer import get_knowledge_indexer

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/search", response_model=KnowledgeSearchResponse)
def search_knowledge(q: str = Query(default=""), top_k: int = Query(default=3, ge=1, le=10)):
    indexer = get_knowledge_indexer()
    results = indexer.search(q, top_k=top_k)
    return KnowledgeSearchResponse(
        query=q,
        results=[KnowledgeSearchResult.model_validate(item) for item in results],
    )


@router.get("/documents", response_model=KnowledgeListResponse)
def list_knowledge_documents():
    indexer = get_knowledge_indexer()
    documents = indexer.list_documents()
    return KnowledgeListResponse(
        total=len(documents),
        documents=[KnowledgeDocument.model_validate(item) for item in documents],
    )


@router.post("/reindex", response_model=KnowledgeReindexResponse)
def reindex_knowledge():
    indexer = get_knowledge_indexer()
    indexed, removed = indexer.reindex_all()
    return KnowledgeReindexResponse(indexed=indexed, removed=removed)


@router.post("/import", response_model=KnowledgeImportResponse, status_code=status.HTTP_201_CREATED)
async def import_knowledge_reference(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    tags: str | None = Form(default=None),
):
    content = await file.read()
    tag_list = [item.strip() for item in (tags or "").split(",") if item.strip()]
    result = import_reference(
        content,
        file.filename or "reference.png",
        title=title,
        tags=tag_list,
    )
    return KnowledgeImportResponse(**result)
