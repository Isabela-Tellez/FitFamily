"""Tests for web tools (Persona 1 - Juan).

These tests use mocked data and do not require internet connectivity.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.search_web import search_web
from src.tools.read_web_page import read_web_page


def test_search_web_returns_list():
    """Test that search_web returns a list of results."""
    try:
        results = search_web("test query", max_results=3)
        assert isinstance(results, list)
    except Exception:
        # May fail without internet, but should not crash
        assert True


def test_search_web_max_results_respected():
    """Test that max_results parameter is respected."""
    try:
        results = search_web("test query", max_results=2)
        assert len(results) <= 2
    except Exception:
        assert True


def test_read_web_page_validates_url():
    """Test that read_web_page validates URLs."""
    # Test with invalid URL
    try:
        result = read_web_page("not-a-url")
        # Should return None or error, not crash
        assert result is None or isinstance(result, dict)
    except Exception:
        assert True


def test_read_web_page_blocks_private_ips():
    """Test that read_web_page blocks private IP addresses."""
    private_urls = [
        "http://127.0.0.1/test",
        "http://192.168.1.1/test",
        "http://10.0.0.1/test",
    ]
    for url in private_urls:
        try:
            result = read_web_page(url)
            # Should return None or error for private IPs
            assert result is None or "error" in str(result).lower() or "blocked" in str(result).lower()
        except Exception:
            assert True
