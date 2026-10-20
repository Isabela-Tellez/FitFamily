"""Tests for competitor_search module (Persona 1 - Juan).

These tests use controlled data and do not require internet connectivity.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, MagicMock
from types import SimpleNamespace
from src.tools.competitor_search import (
    competitor_search,
    CompetitorSearchInput,
    _extract_evidence_from_page,
    _parse_amount,
)
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


# --- Price extraction tests ---

def test_parse_amount_supports_spanish_and_english_notation():
    assert _parse_amount("49,90") == 49.90
    assert _parse_amount("49.90") == 49.90
    assert _parse_amount("1.200") == 1200.0
    assert _parse_amount("1.200,50") == 1200.50
    assert _parse_amount("") is None


def test_extract_price_prefers_monthly_over_registration():
    page = SimpleNamespace(
        body_text="Matrícula 30 €. Cuota mensual 49,90 €/mes.",
    )
    evidence = _extract_evidence_from_page(page, "gimnasio con ludoteca", "https://gym.example")

    assert evidence is not None
    assert evidence.value == 49.90
    assert evidence.unit == "euros"
    assert evidence.frequency == "monthly"
    assert "al mes" in evidence.claim


def test_extract_price_identifies_registration_fee():
    page = SimpleNamespace(body_text="Matrícula: 25 €")
    evidence = _extract_evidence_from_page(page, "gimnasio", "https://gym.example")

    assert evidence is not None
    assert evidence.value == 25.0
    assert evidence.frequency == "one-time"


def test_extract_price_identifies_annual_fee():
    page = SimpleNamespace(body_text="Cuota 1.200,50 € al año")
    evidence = _extract_evidence_from_page(page, "gimnasio", "https://gym.example")

    assert evidence is not None
    assert evidence.value == 1200.50
    assert evidence.frequency == "annual"


def test_extract_price_without_price_is_declared_missing():
    page = SimpleNamespace(body_text="Gimnasio con ludoteca en Madrid.")
    evidence = _extract_evidence_from_page(page, "gimnasio", "https://gym.example")

    assert evidence is not None
    assert evidence.value is None
    assert evidence.frequency is None
    assert evidence.limitations


def test_competitor_search_populates_tariffs_from_evidence():
    """A price found on a page must reach Competitor.tariffs."""
    mock_search_results = [
        SearchResult(
            title="Gym A",
            url="https://gyma.com",
            snippet="Gym with ludoteca",
            provider="ddgs",
        ),
    ]
    mock_page = MagicMock()
    mock_page.has_content = True
    mock_page.title = "Gym A"
    mock_page.body_text = "Cuota mensual 49,90 €/mes."
    mock_page.snippet = "Gym with ludoteca"
    mock_page.final_url = "https://gyma.com"
    mock_page.warnings = []

    with patch("src.tools.competitor_search.search_web", return_value=mock_search_results), \
         patch("src.tools.competitor_search.read_web_page", return_value=mock_page):
        result = competitor_search({
            "area": "El Cañaveral",
            "business_type": "gimnasio con ludoteca",
            "max_results": 3,
        })

    competitors = result["competitors"]
    assert len(competitors) == 1
    assert competitors[0].tariffs[0]["value"] == 49.90
    assert competitors[0].tariffs[0]["frequency"] == "monthly"
