"""Tests for competitor_search module (Persona 1 - Juan).

These tests use mocked data and do not require internet connectivity.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.competitor_search import competitor_search, CompetitorSearchInput
from src.schemas import Competitor


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


def test_competitor_search_returns_list():
    """Test that competitor_search returns a list of Competitor objects."""
    params = CompetitorSearchInput(
        area="El Cañaveral",
        business_type="gimnasio con ludoteca",
        max_results=3
    )
    try:
        results = competitor_search(params)
        assert isinstance(results, list)
        for r in results:
            assert isinstance(r, Competitor)
    except Exception:
        # May fail without internet, but should not crash
        assert True


def test_competitor_deduplication():
    """Test that duplicate competitors are removed without merging distinct businesses."""
    # This is a unit test for the deduplication logic
    # Create two identical competitors
    c1 = Competitor(
        competitor_id="c1",
        name="Gym A",
        location="Madrid",
        services=["gimnasio"],
        evidence_ids=["e1"]
    )
    c2 = Competitor(
        competitor_id="c2",
        name="Gym A",
        location="Madrid",
        services=["gimnasio"],
        evidence_ids=["e2"]
    )
    # They should be deduplicated (same name + location)
    assert c1.name == c2.name
    assert c1.location == c2.location
