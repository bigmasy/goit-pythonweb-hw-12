import pytest
from src.conf.config import Settings, get_settings

def test_get_settings_returns_singleton():
    """Tests that get_settings returns the singleton instance of the configuration."""
    settings1 = get_settings()
    settings2 = get_settings()
    
    # Assert that both calls return the same object instance
    assert settings1 is settings2
    
    # Assert basic structure and values
    assert isinstance(settings1, Settings)
    assert settings1.JWT_ALGORITHM == "HS256"