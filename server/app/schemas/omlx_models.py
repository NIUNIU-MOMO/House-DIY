from pydantic import BaseModel, Field


class OmlxModelConfig(BaseModel):
    """oMLX 模型 alias 配置（运行时）"""

    llm_model: str = Field(description="文本 LLM alias，如 house-llm")
    vlm_model: str = Field(description="默认 VLM alias，如 house-vlm-pro")
    vlm_model_cad: str = Field(default="", description="CAD 线稿专用 VLM alias，空则回退默认")
    vlm_model_marketing: str = Field(default="", description="营销彩图专用 VLM alias，空则回退默认")
    embed_model: str = Field(description="Embedding alias，如 house-embed")


class OmlxModelConfigResponse(OmlxModelConfig):
    """GET 响应：当前配置 + oMLX 可用 alias 列表"""

    available_models: list[str] = Field(default_factory=list)
    omlx_reachable: bool = False


class OmlxModelConfigUpdate(OmlxModelConfig):
    """PUT 请求体"""
