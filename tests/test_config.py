import pytest

from memory_layer.config import get_attribute_config, get_source_reliability


def test_get_source_reliability_known():
    assert get_source_reliability("github") == 0.9


def test_get_source_reliability_unknown_raises():
    with pytest.raises(KeyError):
        get_source_reliability("not_a_real_source")


def test_get_attribute_config_decaying():
    cfg = get_attribute_config("github_stars")
    assert cfg.value_type == "numeric"
    assert cfg.temporal_behavior == "decaying"
    assert cfg.recency_window_days == 30
    assert cfg.half_life_days == 90
    assert cfg.numeric_tolerance == 0.05


def test_get_attribute_config_static():
    cfg = get_attribute_config("job_title")
    assert cfg.temporal_behavior == "static"
    assert cfg.recency_window_days is None
    assert cfg.half_life_days is None


def test_get_attribute_config_unknown_raises():
    with pytest.raises(KeyError):
        get_attribute_config("not_a_real_attribute")
