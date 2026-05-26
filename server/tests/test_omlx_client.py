from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import settings
from app.services.omlx_client import get_omlx_client


@pytest.fixture(autouse=True)
def reset_omlx_client_cache():
    get_omlx_client.cache_clear()
    yield
    get_omlx_client.cache_clear()


@pytest.fixture
def mock_openai():
    with patch("app.services.omlx_client.OpenAI") as mock_cls:
        client = MagicMock()
        mock_cls.return_value = client
        yield client


def _chat_response(content: str):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def test_embed_returns_1024_dim_vectors(mock_openai):
    embedding = SimpleNamespace(embedding=[0.1] * 1024)
    mock_openai.embeddings.create.return_value = SimpleNamespace(data=[embedding])

    result = get_omlx_client().embed(["测试"])

    assert len(result) == 1
    assert len(result[0]) == 1024
    mock_openai.embeddings.create.assert_called_once()


def test_chat_text_returns_content(mock_openai):
    mock_openai.chat.completions.create.return_value = _chat_response("你好，我是设计助手")

    result = get_omlx_client().chat_text([{"role": "user", "content": "你好"}])

    assert result == "你好，我是设计助手"


def test_chat_vision_includes_image(mock_openai):
    mock_openai.chat.completions.create.return_value = _chat_response('{"rooms": []}')

    result = get_omlx_client().chat_vision(
        "识别户型",
        image_base64="abc123",
        mime_type="image/png",
    )

    assert result == '{"rooms": []}'
    call_kwargs = mock_openai.chat.completions.create.call_args.kwargs
    user_content = call_kwargs["messages"][1]["content"]
    assert any(part.get("type") == "image_url" for part in user_content if isinstance(part, dict))


def test_chat_vision_falls_back_on_500(mock_openai, monkeypatch):
    from openai import APIStatusError

    monkeypatch.setattr(settings, "house_diy_omlx_vlm_fallback_enabled", True)
    get_omlx_client.cache_clear()
    mock_openai.chat.completions.create.side_effect = [
        APIStatusError(
            "Internal server error",
            response=MagicMock(status_code=500),
            body={"error": {"message": "Internal server error"}},
        ),
        _chat_response('{"rooms": []}'),
    ]

    result = get_omlx_client().chat_vision(
        "识别户型",
        image_base64="abc123",
        model="house-vlm-pro",
    )

    assert result == '{"rooms": []}'
    assert mock_openai.chat.completions.create.call_count == 2
    assert mock_openai.chat.completions.create.call_args_list[0].kwargs["model"] == "house-vlm-pro"
    assert mock_openai.chat.completions.create.call_args_list[1].kwargs["model"] == "house-vlm"


def test_chat_vision_no_fallback_when_disabled(mock_openai, monkeypatch):
    from openai import APIStatusError

    monkeypatch.setattr(settings, "house_diy_omlx_vlm_fallback_enabled", False)
    get_omlx_client.cache_clear()
    mock_openai.chat.completions.create.side_effect = APIStatusError(
        "Internal server error",
        response=MagicMock(status_code=500),
        body={"error": {"message": "Internal server error"}},
    )

    with pytest.raises(APIStatusError):
        get_omlx_client().chat_vision(
            "识别户型",
            image_base64="abc123",
            model="house-vlm-pro",
        )

    assert mock_openai.chat.completions.create.call_count == 1
    assert mock_openai.chat.completions.create.call_args.kwargs["model"] == "house-vlm-pro"


def test_client_singleton(mock_openai):
    assert get_omlx_client() is get_omlx_client()
