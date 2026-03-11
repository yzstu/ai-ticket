"""
Pytest configuration and shared fixtures
"""
import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.config.settings import Settings


@pytest.fixture
def test_settings():
    """Test settings fixture with default values"""
    return Settings()


@pytest.fixture
def sample_stock_data():
    """Sample stock data for testing"""
    return {
        'code': '600519',
        'name': '贵州茅台',
        'close': 1800.0,
        'volume': 1000000,
        'open': 1790.0,
        'high': 1810.0,
        'low': 1785.0
    }


@pytest.fixture
def mock_cache_dir(tmp_path):
    """Mock cache directory for testing"""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return str(cache_dir)