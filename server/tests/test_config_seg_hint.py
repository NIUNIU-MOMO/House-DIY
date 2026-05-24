"""config seg hint 开关与 seg_hint_active 辅助方法"""

from app.core.config import Settings


def test_seg_hint_active_requires_seg_enabled():
    cfg = Settings(house_diy_seg_enabled=False, house_diy_seg_hint_enabled=True)
    assert cfg.seg_hint_active() is False


def test_seg_hint_active_when_both_enabled():
    cfg = Settings(house_diy_seg_enabled=True, house_diy_seg_hint_enabled=True)
    assert cfg.seg_hint_active() is True


def test_seg_hint_disabled_when_hint_flag_off():
    cfg = Settings(house_diy_seg_enabled=True, house_diy_seg_hint_enabled=False)
    assert cfg.seg_hint_active() is False
