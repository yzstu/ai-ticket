"""
Tests for settings configuration
"""
from src.config.settings import Settings


def test_settings_creation():
    """Test that settings can be created"""
    settings = Settings()
    assert settings is not None


def test_settings_default_values():
    """Test that settings have correct default values"""
    settings = Settings()
    assert settings.api.api_port == 8000
    assert settings.cache.cache_ttl_hours == 24
    assert settings.parallel.max_workers == 0


def test_settings_as_dict():
    """Test that settings can be converted to dict"""
    settings = Settings()
    settings_dict = settings.as_dict()
    assert isinstance(settings_dict, dict)
    assert "api" in settings_dict
    assert "cache" in settings_dict
    assert "parallel" in settings_dict