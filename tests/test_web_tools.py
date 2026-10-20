"""Tests for web tools (Persona 1 - Juan).

These tests use mocked providers and do not require internet connectivity.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, MagicMock
from src.tools.search_web import search_web, SearchResult
from src.tools.read_web_page import read_web_page, PageReadResult


def test_search_web_returns_list():
    """Test that search_web returns a list of SearchResult objects."""
    mock_results = [
        {"title": "Test Result 1", "url": "https://example.com/1", "snippet": "Snippet 1"},
        {"title": "Test Result 2", "url": "https://example.com/2", "snippet": "Snippet 2"},
    ]
    with patch("src.tools.search_web._get_search_provider", return_value="ddgs"), \
         patch("src.tools.search_web._search_ddgs", return_value=mock_results):
        results = search_web("test query", max_results=5)
        assert isinstance(results, list)
        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)
        assert results[0].title == "Test Result 1"
        assert results[0].url == "https://example.com/1"


def test_search_web_validates_empty_query():
    """Test that search_web raises ValueError for empty query."""
    import pytest
    with pytest.raises(ValueError, match="non-empty string"):
        search_web("")


def test_search_web_validates_max_results():
    """Test that search_web raises ValueError for invalid max_results."""
    import pytest
    with pytest.raises(ValueError, match="positive integer"):
        search_web("test", max_results=0)
    with pytest.raises(ValueError, match="positive integer"):
        search_web("test", max_results=-1)


def test_search_web_caps_max_results_at_20():
    """Test that max_results is capped at 20."""
    mock_results = [{"title": f"Result {i}", "url": f"https://example.com/{i}", "snippet": f"Snippet {i}"} for i in range(25)]
    with patch("src.tools.search_web._get_search_provider", return_value="ddgs"), \
         patch("src.tools.search_web._search_ddgs", return_value=mock_results):
        results = search_web("test query", max_results=30)
        assert len(results) <= 20


def test_search_web_no_provider_raises():
    """Test that search_web raises RuntimeError when no provider is available."""
    import pytest
    with patch("src.tools.search_web._get_search_provider", return_value="none"):
        with pytest.raises(RuntimeError, match="No search provider available"):
            search_web("test query")


def test_search_web_empty_results():
    """Test that search_web handles empty results gracefully."""
    with patch("src.tools.search_web._get_search_provider", return_value="ddgs"), \
         patch("src.tools.search_web._search_ddgs", return_value=[]):
        results = search_web("test query", max_results=5)
        assert isinstance(results, list)
        assert len(results) == 0


def test_search_web_deduplicates_urls():
    """Test that search_web deduplicates results by URL."""
    mock_results = [
        {"title": "Result 1", "url": "https://example.com/1", "snippet": "Snippet 1"},
        {"title": "Result 1 Dup", "url": "https://example.com/1", "snippet": "Snippet 1 Dup"},
        {"title": "Result 2", "url": "https://example.com/2", "snippet": "Snippet 2"},
    ]
    with patch("src.tools.search_web._get_search_provider", return_value="ddgs"), \
         patch("src.tools.search_web._search_ddgs", return_value=mock_results):
        results = search_web("test query", max_results=10)
        assert len(results) == 2


def test_read_web_page_returns_page_read_result():
    """Test that read_web_page returns a PageReadResult."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/html"}
    mock_response.text = "<html><head><title>Test Page</title></head><body><p>Test content</p></body></html>"
    mock_response.url = "https://example.com/test"

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_response

    with patch("src.tools.read_web_page.httpx.Client", return_value=mock_client):
        result = read_web_page("https://example.com/test")
        assert isinstance(result, PageReadResult)
        assert result.status == "200"
        assert result.title == "Test Page"


def test_read_web_page_validates_url():
    """Test that read_web_page rejects invalid URLs."""
    import pytest
    with pytest.raises(ValueError, match="http:// or https://"):
        read_web_page("not-a-url")


def test_read_web_page_blocks_private_ips():
    """Test that read_web_page blocks private IP addresses."""
    import pytest
    private_urls = [
        "http://127.0.0.1/test",
        "http://192.168.1.1/test",
        "http://10.0.0.1/test",
        "http://[::1]/test",
    ]
    for url in private_urls:
        with pytest.raises(RuntimeError, match="private IP|denied|blocked|not allowed"):
            read_web_page(url)


def test_read_web_page_blocks_dns_rebinding():
    """DNS resolution to a private IP must be blocked (TOCTOU mitigation)."""
    import pytest
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/html"}
    mock_response.text = "<html><body>ok</body></html>"
    mock_response.url = "https://example.com/test"

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_response

    with patch("src.tools.read_web_page._resolve_host", side_effect=[["93.184.216.34"], ["127.0.0.1"]]), \
         patch("src.tools.read_web_page.httpx.Client", return_value=mock_client):
        with pytest.raises(RuntimeError, match="not allowed|denied"):
            read_web_page("https://example.com/test")


def test_read_web_page_blocks_redirect_to_private():
    """A redirect to a private destination must be blocked."""
    import pytest
    redirect_response = MagicMock()
    redirect_response.status_code = 302
    redirect_response.headers = {"location": "http://127.0.0.1/secret", "content-type": "text/html"}
    redirect_response.url = "https://example.com/start"

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = redirect_response

    with patch("src.tools.read_web_page._resolve_host", return_value=["93.184.216.34"]), \
         patch("src.tools.read_web_page.httpx.Client", return_value=mock_client):
        with pytest.raises(RuntimeError, match="disallowed|denied|not allowed"):
            read_web_page("https://example.com/start")


def test_read_web_page_rejects_credentials_in_url():
    """URLs with embedded credentials must be rejected."""
    import pytest
    with pytest.raises(ValueError, match="Credentials"):
        read_web_page("http://user:pass@example.com/test")


def test_read_web_page_rejects_non_standard_port():
    """Non-standard ports must be rejected."""
    import pytest
    with patch("src.tools.read_web_page._resolve_host", return_value=["93.184.216.34"]):
        with pytest.raises(RuntimeError, match="Port not allowed"):
            read_web_page("https://example.com:8080/test")


def test_read_web_page_blocks_redirect_chain():
    """A redirect chain exceeding the limit must be blocked."""
    import pytest
    redirect_response = MagicMock()
    redirect_response.status_code = 302
    redirect_response.headers = {"location": "https://example.com/next", "content-type": "text/html"}
    redirect_response.url = "https://example.com/start"

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = redirect_response

    with patch("src.tools.read_web_page._resolve_host", return_value=["93.184.216.34"]), \
         patch("src.tools.read_web_page.httpx.Client", return_value=mock_client):
        with pytest.raises(RuntimeError, match="Too many redirects"):
            read_web_page("https://example.com/start")


def test_validating_backend_connects_to_validated_ip():
    """The transport must connect to the resolved IP, not the hostname."""
    import socket
    from unittest.mock import patch, MagicMock
    from src.tools.read_web_page import _ValidatingBackend, _resolve_host

    with patch("src.tools.read_web_page._resolve_host", return_value=["93.184.216.34"]), \
         patch("socket.create_connection") as mock_conn:
        mock_sock = MagicMock()
        mock_conn.return_value = mock_sock
        backend = _ValidatingBackend()
        stream = backend.connect_tcp("example.com", 443, timeout=5.0)
        # Connected to the IP, not the hostname
        mock_conn.assert_called_once()
        assert mock_conn.call_args[0][0] == ("93.184.216.34", 443)
        assert stream is not None


def test_validating_backend_blocks_private_resolved_ip():
    """If DNS resolves to a private IP, the backend must refuse to connect."""
    import pytest
    from unittest.mock import patch
    from src.tools.read_web_page import _ValidatingBackend

    with patch("src.tools.read_web_page._resolve_host", return_value=["127.0.0.1"]):
        backend = _ValidatingBackend()
        with pytest.raises(RuntimeError, match="not allowed|denied"):
            backend.connect_tcp("example.com", 443, timeout=5.0)


def test_read_web_page_rejects_bad_scheme():
    """Non-http(s) schemes must be rejected."""
    import pytest
    with pytest.raises(ValueError, match="http:// or https://"):
        read_web_page("ftp://example.com/test")
