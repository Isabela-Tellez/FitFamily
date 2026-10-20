"""Tests for the search limits declared in the brief (Persona 1 - Juan)."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, MagicMock

from src.schemas import ResearchBrief
from src.agents.researcher import (
    run_research,
    resolve_max_results,
    DEFAULT_MAX_RESULTS,
    MAX_RESULTS_LIMIT,
)


def _brief(**kwargs):
    params = dict(
        business_type="gimnasio con ludoteca",
        location="Madrid",
        study_area="El Cañaveral",
        questions=["precios"],
    )
    params.update(kwargs)
    return ResearchBrief(**params)


# --- resolve_max_results ---

def test_resolve_max_results_default():
    assert resolve_max_results(None) == DEFAULT_MAX_RESULTS
    assert resolve_max_results({}) == DEFAULT_MAX_RESULTS
    assert resolve_max_results({"max_pages": 3}) == DEFAULT_MAX_RESULTS


def test_resolve_max_results_uses_brief_value():
    assert resolve_max_results({"max_results": 12}) == 12


def test_resolve_max_results_caps_at_tool_limit():
    assert resolve_max_results({"max_results": 500}) == MAX_RESULTS_LIMIT


def test_resolve_max_results_rejects_invalid_values():
    assert resolve_max_results({"max_results": 0}) == DEFAULT_MAX_RESULTS
    assert resolve_max_results({"max_results": -3}) == DEFAULT_MAX_RESULTS
    assert resolve_max_results({"max_results": "muchos"}) == DEFAULT_MAX_RESULTS
    assert resolve_max_results({"max_results": True}) == DEFAULT_MAX_RESULTS


# --- run_research honours the limits ---

def test_run_research_uses_max_results_from_brief():
    """The limit declared in the brief must reach the tools."""
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = MagicMock(
        status_code=200,
        headers={"content-type": "text/html"},
        text="<html><body>ok</body></html>",
        url="https://example.com",
    )

    with patch("src.agents.researcher.search_web", return_value=[]) as mock_search, \
         patch("src.agents.researcher.competitor_search",
               return_value={"competitors": [], "evidences": []}) as mock_comp:
        run_research(_brief(search_limits={"max_results": 12}))

    assert mock_search.call_args.kwargs["max_results"] == 12
    assert mock_comp.call_args[0][0]["max_results"] == 12


def test_run_research_defaults_when_no_limits_given():
    with patch("src.agents.researcher.search_web", return_value=[]) as mock_search, \
         patch("src.agents.researcher.competitor_search",
               return_value={"competitors": [], "evidences": []}) as mock_comp:
        run_research(_brief())

    assert mock_search.call_args.kwargs["max_results"] == DEFAULT_MAX_RESULTS
    assert mock_comp.call_args[0][0]["max_results"] == DEFAULT_MAX_RESULTS


def test_run_research_caps_brief_limit():
    with patch("src.agents.researcher.search_web", return_value=[]) as mock_search, \
         patch("src.agents.researcher.competitor_search",
               return_value={"competitors": [], "evidences": []}) as mock_comp:
        run_research(_brief(search_limits={"max_results": 999}))

    assert mock_search.call_args.kwargs["max_results"] == MAX_RESULTS_LIMIT
    assert mock_comp.call_args[0][0]["max_results"] == MAX_RESULTS_LIMIT
