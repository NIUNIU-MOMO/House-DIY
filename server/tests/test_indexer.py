import pytest

from app.schemas.floorplan import FloorPlanModel
from app.services.design_spec_generator import build_rag_query, generate_design_spec
from app.services.knowledge.indexer import KnowledgeIndexer, get_knowledge_indexer, rag_search

SAMPLE_FLOORPLAN = {
    "scale": 100.0,
    "status": "confirmed",
    "walls": [{"id": "w1", "points": [{"x": 0, "y": 0}, {"x": 100, "y": 0}], "thickness": 0.2}],
    "rooms": [
        {
            "id": "r1",
            "name": "客厅",
            "polygon": [{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 100, "y": 100}, {"x": 0, "y": 100}],
            "area": 12.0,
        }
    ],
    "openings": [],
}

SAMPLE_SPEC_JSON = """
{
  "version": 1,
  "globalStyle": "现代简约",
  "ragContextIds": [],
  "rooms": [{
    "id": "r1",
    "name": "客厅",
    "style": "现代简约",
    "palette": [],
    "furniture": [],
    "render2d": {"prompt": "modern living room", "negative": "blurry", "workflow": "flux_interior_t2i_api"}
  }]
}
"""


class FakeEmbedClient:
    def embed(self, texts, **kwargs):
        vectors = []
        for text in texts:
            seed = sum(ord(char) for char in text) % 997
            vectors.append([((seed + index) % 17) / 17.0 for index in range(8)])
        return vectors

    def chat_text(self, messages, **kwargs):
        return SAMPLE_SPEC_JSON


@pytest.fixture
def vault_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.knowledge.indexer.settings.house_diy_vault_path", str(tmp_path))
    get_knowledge_indexer.cache_clear()
    return tmp_path


def test_index_document_and_search(vault_dir):
    indexer = KnowledgeIndexer(vault_root=vault_dir, omlx_client=FakeEmbedClient())
    indexer.index_document(
        "Cases/demo.md",
        "现代简约客厅，暖白墙面，原木家具，大量自然光",
        "现代简约客厅",
        "case",
        "Cases/demo.md",
    )
    results = indexer.search("现代简约 客厅", top_k=1)
    assert len(results) == 1
    assert results[0]["title"] == "现代简约客厅"
    assert results[0]["score"] > 0


def test_reindex_all_from_markdown(vault_dir):
    cases_dir = vault_dir / "Cases"
    cases_dir.mkdir(parents=True)
    note = cases_dir / "2026-05-20-demo.md"
    note.write_text(
        """---
type: design_case
---
# 北欧风两居
暖白与浅橡木，强调自然采光。
""",
        encoding="utf-8",
    )
    indexer = KnowledgeIndexer(vault_root=vault_dir, omlx_client=FakeEmbedClient())
    indexed, removed = indexer.reindex_all()
    assert indexed == 1
    assert removed == 0
    assert indexer.list_documents()[0]["title"] == "北欧风两居"


def test_rag_search_used_in_design_spec(vault_dir):
    indexer = KnowledgeIndexer(vault_root=vault_dir, omlx_client=FakeEmbedClient())
    indexer.index_document(
        "Cases/ref.md",
        "轻奢风格参考，金属线条与大理石",
        "轻奢参考",
        "case",
        "Cases/ref.md",
    )
    floorplan = FloorPlanModel.model_validate(SAMPLE_FLOORPLAN)
    spec = generate_design_spec(
        "轻奢风格",
        floorplan,
        use_rag=True,
        omlx_client=FakeEmbedClient(),
    )
    assert spec.globalStyle
    assert build_rag_query("轻奢", floorplan).startswith("轻奢")


@pytest.mark.asyncio
async def test_knowledge_api_search(client, vault_dir, monkeypatch):
    monkeypatch.setattr("app.api.knowledge.get_knowledge_indexer", lambda: KnowledgeIndexer(vault_dir, FakeEmbedClient()))
    indexer = KnowledgeIndexer(vault_root=vault_dir, omlx_client=FakeEmbedClient())
    indexer.index_document("Cases/a.md", "北欧客厅", "北欧客厅", "case", "Cases/a.md")

    resp = await client.get("/api/v1/knowledge/search?q=北欧&top_k=1")
    assert resp.status_code == 200
    assert resp.json()["results"]

    docs = await client.get("/api/v1/knowledge/documents")
    assert docs.status_code == 200
    assert docs.json()["total"] >= 1

    reindex = await client.post("/api/v1/knowledge/reindex")
    assert reindex.status_code == 200
