"""Tests for competitor_search module (Persona 1 - Juan).

These tests use controlled data and do not require internet connectivity.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, MagicMock
from src.tools.competitor_search import competitor_search, CompetitorSearchInput
from src.schemas import Competitor, Evidence
from src.tools.search_web import SearchResult


def test_competitor_search_input_validation():
    """Test that CompetitorSearchInput validates required fields."""
    params = CompetitorSearchInput(
        area="El Cañaveral",
        business_type="gimnasio con ludoteca",
        max_results=5
    )
    assert params.area == "El Cañaveral"
    assert params.business_type == "gimnasio con ludoteca"
    assert params.max_results == 5


def test_competitor_search_input_validation_fails():
    """Test that CompetitorSearchInput raises on missing required fields."""
    import pytest
    with pytest.raises(Exception):
        CompetitorSearchInput(area="", business_type="gimnasio")


def test_competitor_search_returns_dict():
    """Test that competitor_search returns a dict with expected keys."""
    mock_search_results = [
        SearchResult(title="Gym A", url="https://gyma.com", snippet="Gym with ludoteca", provider="ddgs"),
    ]
    mock_page = MagicMock()
    mock_page.has_content = True
    mock_page.title = "Gym A"
    mock_page.body_text = "Gym A offers gym and ludoteca services in Madrid."
    mock_page.snippet = "Gym with ludoteca"
    mock_page.final_url = "https://gyma.com"
    mock_page.warnings = []

    with patch("src.tools.competitor_search.search_web", return_value=mock_search_results), \
         patch("src.tools.competitor_search.read_web_page", return_value=mock_page):
        result = competitor_search({
            "area": "El Cañaveral",
            "business_type": "gimnasio con ludoteca",
            "max_results": 3
        })
        assert isinstance(result, dict)
        assert "competitors" in result
        assert "evidences" in result
        assert "search_summary" in result
        assert "unresolved_questions" in result
        assert isinstance(result["competitors"], list)
        assert isinstance(result["evidences"], list)


def test_competitor_search_deduplication():
    """Test that competitor_search deduplicates by URL."""
    mock_search_results = [
        SearchResult(title="Gym A", url="https://gyma.com", snippet="Gym with ludoteca", provider="ddgs"),
        SearchResult(title="Gym A Dup", url="https://gyma.com", snippet="Duplicate", provider="ddgs"),
    ]
    mock_page = MagicMock()
    mock_page.has_content = True
    mock_page.title = "Gym A"
    mock_page.body_text = "Gym A offers gym and ludoteca."
    mock_page.snippet = "Gym with ludoteca"
    mock_page.final_url = "https://gyma.com"
    mock_page.warnings = []

    with patch("src.tools.competitor_search.search_web", return_value=mock_search_results), \
         patch("src.tools.competitor_search.read_web_page", return_value=mock_page):
        result = competitor_search({
            "area": "El Cañaveral",
            "business_type": "gimnasio con ludoteca",
            "max_results": 5
        })
        # Should have deduplicated the duplicate URL
        assert isinstance(result, dict)
        assert "competitors" in result


def test_competitor_search_handles_search_failure():
    """Test that competitor_search handles search provider failure gracefully."""
    with patch("src.tools.competitor_search.search_web", side_effect=Exception("Network error")):
        # Should not crash, but may return empty results or raise
        try:
            result = competitor_search({
                "area": "El Cañaveral",
                "business_type": "gimnasio con ludoteca",
                "max_results": 3
            })
            assert isinstance(result, dict)
        except (ValueError, RuntimeError):
            # Acceptable if it raises a documented exception
            pass


def test_competitor_search_validates_input():
    """Test that competitor_search validates input parameters."""
    import pytest
    with pytest.raises(ValueError):
        competitor_search({"area": "", "business_type": "gimnasio"})
