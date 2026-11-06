"""Tests deterministas para search_web (Juan - Persona 1) - cobertura completa."""
import os, sys
from unittest.mock import patch, MagicMock
import pytest
sys.path.insert(0, ".")

from src.tools.search_web import (
    _get_search_provider, SearchResult,
    _normalize_url, _search_tavily, _search_ddgs,
    search_web,
)


def test_provider_tavily_when_key_set():
    old = os.environ.get("TAVILY_API_KEY")
    os.environ["TAVILY_API_KEY"] = "fake_key"
    import src.tools.search_web as sw
    sw._SEARCH_PROVIDER = None
    assert _get_search_provider() == "tavily"
    if old is not None:
        os.environ["TAVILY_API_KEY"] = old
    else:
        os.environ.pop("TAVILY_API_KEY", None)
    sw._SEARCH_PROVIDER = None


def test_provider_none_when_no_key_no_ddgs():
    old = os.environ.get("TAVILY_API_KEY")
    os.environ.pop("TAVILY_API_KEY", None)
    import src.tools.search_web as sw
    sw._SEARCH_PROVIDER = None
    with patch("src.tools.search_web.DDGS_AVAILABLE", False):
        assert _get_search_provider() == "none"
    if old is not None:
        os.environ["TAVILY_API_KEY"] = old


def test_search_result_model():
    r = SearchResult(title="T", url="https://example.com", snippet="S")
    assert r.provider == "unknown"


def test_search_result_validates_url():
    with pytest.raises(ValueError):
        SearchResult(title="T", url="ftp://bad.com", snippet="S")


def test_normalize_url():
    url = "https://example.com/page?q=1#frag"
    norm = _normalize_url(url)
    assert "example.com/page" in norm


def test_normalize_url_no_fragment():
    url = "https://example.com/path"
    assert _normalize_url(url) == "https://example.com/path"


def test_search_result_provider_field():
    r = SearchResult(title="T", url="https://example.com", snippet="S", provider="tavily")
    assert r.provider == "tavily"


def test_search_web_validates_max_results_zero():
    with pytest.raises(ValueError):
        search_web("query", max_results=0)


def test_search_web_validates_max_results_negative():
    with pytest.raises(ValueError):
        search_web("query", max_results=-1)


def test_search_web_validates_max_results_negative():
    with pytest.raises(ValueError):
        search_web("query", max_results=-5)


def test_search_web_validates_empty_query():
    with pytest.raises(ValueError):
        search_web("")


def test_search_web_validates_whitespace_query():
    with pytest.raises(ValueError):
        search_web("   ")