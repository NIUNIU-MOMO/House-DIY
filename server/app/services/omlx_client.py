from functools import lru_cache
from typing import Any

from openai import OpenAI

from app.core.config import settings


class OmlxClient:
    """oMLX OpenAI 兼容客户端封装"""

    def __init__(self) -> None:
        self._client = OpenAI(
            base_url=settings.house_diy_omlx_base_url,
            api_key=settings.house_diy_omlx_api_key or "local",
        )
        self.llm_model = settings.house_diy_omlx_llm_model
        self.vlm_model = settings.house_diy_omlx_vlm_model
        self.embed_model = settings.house_diy_omlx_embed_model

    def chat_text(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        **kwargs: Any,
    ) -> str:
        """
        文本对话

        @param messages OpenAI 格式消息列表
        @param model 模型 alias，默认 house-llm
        @return 助手回复文本
        """
        response = self._client.chat.completions.create(
            model=model or self.llm_model,
            messages=messages,
            **kwargs,
        )
        return response.choices[0].message.content or ""

    def chat_vision(
        self,
        prompt: str,
        image_base64: str,
        mime_type: str = "image/png",
        model: str | None = None,
        **kwargs: Any,
    ) -> str:
        """
        视觉对话（VLM）

        @param prompt 用户提示词
        @param image_base64 图片 base64 内容（不含 data: 前缀）
        @param mime_type 图片 MIME 类型
        @param model 模型 alias，默认 house-vlm-pro
        @return 助手回复文本
        """
        messages = [
            {"role": "system", "content": "你是户型图解析助手，只输出 JSON。"},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{image_base64}"},
                    },
                ],
            },
        ]
        response = self._client.chat.completions.create(
            model=model or self.vlm_model,
            messages=messages,
            **kwargs,
        )
        return response.choices[0].message.content or ""

    def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        """
        文本向量化

        @param texts 待嵌入文本列表
        @param model 模型 alias，默认 house-embed
        @return 向量列表
        """
        if not texts:
            return []

        response = self._client.embeddings.create(
            model=model or self.embed_model,
            input=texts,
        )
        return [item.embedding for item in response.data]


@lru_cache
def get_omlx_client() -> OmlxClient:
    return OmlxClient()
