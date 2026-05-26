from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    house_diy_vault_path: str = "~/House-DIY-Vault"
    house_diy_omlx_base_url: str = "http://127.0.0.1:8000/v1"
    house_diy_omlx_api_key: str = ""
    house_diy_omlx_llm_model: str = "house-llm"
    house_diy_omlx_vlm_model: str = "house-vlm-pro"
    house_diy_omlx_vlm_model_fallback: str = "house-vlm"
    house_diy_omlx_vlm_fallback_enabled: bool = False
    house_diy_omlx_vlm_model_cad: str = ""
    house_diy_omlx_vlm_model_marketing: str = ""
    house_diy_omlx_embed_model: str = "house-embed"
    house_diy_seg_enabled: bool = False
    house_diy_seg_hint_enabled: bool = True
    house_diy_seg_model_path: str = ""
    house_diy_comfyui_base_url: str = "http://127.0.0.1:8188"
    house_diy_comfyui_render_timeout: float = 900.0
    house_diy_comfyui_depth_strength: float = 0.65
    house_diy_omlx_log_path: str = ""
    house_diy_comfyui_log_path: str = "~/ComfyUI/comfyui.log"
    house_diy_vault_log_path: str = ""
    house_diy_api_log_path: str = ""
    house_diy_database_url: str = "sqlite:///./house_diy.db"
    house_diy_upload_dir: str = "./data/uploads"
    house_diy_output_dir: str = "./data/output"
    house_diy_projects_dir: str = "./data/projects"
    house_diy_output_root: str = ""

    def output_root(self) -> Path:
        """
        有效输出根目录：settings.local.json > HOUSE_DIY_OUTPUT_ROOT > projects_dir

        @return 输出根目录绝对路径
        """
        from app.services.settings_storage import resolve_output_root

        env_fallback = self.house_diy_output_root or self.house_diy_projects_dir
        return resolve_output_root(env_fallback)

    def vault_path(self) -> Path:
        return Path(self.house_diy_vault_path).expanduser()

    def vault_templates_path(self) -> Path:
        repo_root = Path(__file__).resolve().parents[2]
        return repo_root.parent / "vault-templates"

    def api_log_path(self) -> Path:
        if self.house_diy_api_log_path:
            return Path(self.house_diy_api_log_path).expanduser()
        repo_root = Path(__file__).resolve().parents[2]
        return repo_root.parent / ".run" / "api.log"

    def omlx_admin_url(self) -> str:
        base = self.house_diy_omlx_base_url.rstrip("/")
        if base.endswith("/v1"):
            base = base[:-3]
        return f"{base}/admin"

    def comfyui_web_url(self) -> str:
        return self.house_diy_comfyui_base_url.rstrip("/")

    def seg_hint_active(self) -> bool:
        """
        Seg hint 是否生效（需同时开启 seg 与 hint 开关）

        @return True 表示应在 VLM Step2 注入 seg 区域 hint
        """
        return self.house_diy_seg_enabled and self.house_diy_seg_hint_enabled

    def vlm_model_for_plan_type(self, plan_type: str) -> str:
        """
        按图源类型选择 VLM alias，未配置专用 alias 时回退默认 house-vlm-pro

        @param plan_type 图源类型 cad_lineart / marketing_color / unknown
        @return oMLX VLM 模型 alias
        """
        if plan_type == "cad_lineart" and self.house_diy_omlx_vlm_model_cad:
            return self.house_diy_omlx_vlm_model_cad
        if plan_type == "marketing_color" and self.house_diy_omlx_vlm_model_marketing:
            return self.house_diy_omlx_vlm_model_marketing
        return self.house_diy_omlx_vlm_model


settings = Settings()
