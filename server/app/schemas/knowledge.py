from pydantic import BaseModel, Field


class KnowledgeDocument(BaseModel):
    id: str
    title: str
    type: str
    meta: str = ""
    path: str = ""
    source: str = "internal"


class KnowledgeSearchResult(BaseModel):
    id: str
    title: str
    score: float
    desc: str = ""
    type: str = "case"


class KnowledgeSearchResponse(BaseModel):
    query: str
    results: list[KnowledgeSearchResult]


class KnowledgeListResponse(BaseModel):
    total: int
    documents: list[KnowledgeDocument]


class KnowledgeImportResponse(BaseModel):
    path: str
    title: str
    indexed: bool


class KnowledgeReindexResponse(BaseModel):
    indexed: int
    removed: int
