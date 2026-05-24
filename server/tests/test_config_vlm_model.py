"""config VLM alias 按图源类型解析"""

from app.core.config import Settings


def test_vlm_model_for_plan_type_defaults_to_base():
    cfg = Settings(
        house_diy_omlx_vlm_model="house-vlm",
        house_diy_omlx_vlm_model_cad="",
        house_diy_omlx_vlm_model_marketing="",
    )
    assert cfg.vlm_model_for_plan_type("cad_lineart") == "house-vlm"
    assert cfg.vlm_model_for_plan_type("marketing_color") == "house-vlm"
    assert cfg.vlm_model_for_plan_type("unknown") == "house-vlm"


def test_vlm_model_for_plan_type_uses_specialized_aliases():
    cfg = Settings(
        house_diy_omlx_vlm_model="house-vlm",
        house_diy_omlx_vlm_model_cad="house-vlm-cad",
        house_diy_omlx_vlm_model_marketing="house-vlm-mkt",
    )
    assert cfg.vlm_model_for_plan_type("cad_lineart") == "house-vlm-cad"
    assert cfg.vlm_model_for_plan_type("marketing_color") == "house-vlm-mkt"
    assert cfg.vlm_model_for_plan_type("unknown") == "house-vlm"
