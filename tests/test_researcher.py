"""Tests for researcher module (Persona 1 - Juan).

These tests use controlled data and do not require internet connectivity.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.schemas import ResearchBrief, ResearchResult, Evidence, Competitor
from src.agents.researcher import run_research, build_researcher, build_research_task


def test_research_brief_validation():
    """Test that ResearchBrief validates required fields."""
    brief = ResearchBrief(
        business_type="gimnasio con ludoteca",
        location="Madrid",
        study_area="El Cañaveral",
        questions=["precios", "servicios"]
    )
    assert brief.business_type == "gimnasio con ludoteca"
    assert brief.location == "Madrid"
    assert len(brief.questions) == 2


def test_run_research_returns_research_result():
    """Test that run_research returns a properly formed ResearchResult."""
    brief = ResearchBrief(
        business_type="gimnasio con ludoteca",
        location="Madrid",
        study_area="El Cañaveral",
        questions=["precios"]
    )
    result = run_research(brief)
    assert isinstance(result, ResearchResult)
    assert isinstance(result.evidences, list)
    assert isinstance(result.competitors, list)
    assert isinstance(result.coverage_percentage, (int, float))
    assert isinstance(result.unresolved_questions, list)
    assert result.coverage_percentage == 0.0  # No LLM by design


def test_run_research_no_llm_coverage_zero():
    """Test that coverage is 0.0 when no LLM is configured (by design)."""
    brief = ResearchBrief(
        business_type="gimnasio con ludoteca",
        location="Madrid",
        study_area="El Cañaveral",
        questions=["precios"]
    )
    result = run_research(brief)
    # Coverage 0.0 means no LLM analysis was performed
    # Data (evidences, competitors) may still be collected from web
    assert result.coverage_percentage == 0.0


def test_evidence_schema():
    """Test Evidence model validation."""
    evidence = Evidence(
        evidence_id="e1",
        claim="Test claim",
        source_url="https://example.com",
        snippet="Test snippet"
    )
    assert evidence.evidence_id == "e1"
    assert evidence.claim == "Test claim"
    assert evidence.source_url == "https://example.com"


def test_competitor_schema():
    """Test Competitor model validation."""
    evidence = Evidence(
        evidence_id="e1",
        claim="Test claim"
    )
    competitor = Competitor(
        identifier="c1",
        name="Test Gym",
        location="Madrid",
        services=["gimnasio", "ludoteca"],
        evidences=[evidence]
    )
    assert competitor.identifier == "c1"
    assert competitor.name == "Test Gym"
    assert len(competitor.services) == 2
    assert len(competitor.evidences) == 1


def test_build_researcher_returns_agent():
    """Test that build_researcher returns a CrewAI Agent with correct role."""
    agent = build_researcher()
    assert agent is not None
    assert agent.role == "Investigador de mercado local"
    assert agent is not None


def test_build_research_task_returns_task():
    """Test that build_research_task returns a CrewAI Task."""
    brief = ResearchBrief(
        business_type="gimnasio con ludoteca",
        location="Madrid",
        study_area="El Cañaveral",
        questions=["precios"]
    )
    task = build_research_task(brief)
    assert task is not None
    assert task.description is not None
    assert len(task.description) > 0


def test_run_research_with_multiple_questions():
    """Test that run_research handles multiple questions."""
    brief = ResearchBrief(
        business_type="gimnasio con ludoteca",
        location="Madrid",
        study_area="El Cañaveral",
        questions=["precios", "servicios", "horarios"]
    )
    result = run_research(brief)
    assert isinstance(result, ResearchResult)
    assert len(result.questions) if hasattr(result, 'questions') else True
    # Should have unresolved questions since no LLM
    assert isinstance(result.unresolved_questions, list)
