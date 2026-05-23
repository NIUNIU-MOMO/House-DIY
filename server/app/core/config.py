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
    house_diy_omlx_vlm_model: str = "house-vlm"
    house_diy_omlx_embed_model: str = "house-embed"
    house_diy_comfyui_base_url: str = "http://127.0.0.1:8188"
    house_diy_database_url: str = "sqlite:///./house_diy.db"
    house_diy_upload_dir: str = "./data/uploads"
    house_diy_output_dir: str = "./data/output"
    house_diy_projects_dir: str = "./data/projects"

    def vault_path(self) -> Path:
        return Path(self.house_diy_vault_path).expanduser()

    def vault_templates_path(self) -> Path:
        repo_root = Path(__file__).resolve().parents[2]
        return repo_root.parent / "vault-templates"


settings = Settings()
