import pytest

from app.services.omlx_client import get_omlx_client


@pytest.mark.integration
def test_embed_live_returns_1024_dim():
    client = get_omlx_client()
    vectors = client.embed(["House-DIY 集成测试"])
    assert len(vectors) == 1
    assert len(vectors[0]) == 1024
