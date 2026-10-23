"""Pruebas del redactor con respuestas simuladas, sin llamadas externas."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.agents.strategic_writer import run_writing
from src.reporting.writing_models import WritingClaim, WritingOutput
from src.schemas import Evidence, ResearchBrief, ResearchResult


@pytest.fixture
def brief():
    return ResearchBrief(
        business_type="gimnasio con ludoteca",
        location="Madrid",
        study_area="El Cañaveral",
    )


@pytest.fixture
def simulated_response():
    """Sustituye la construcción del agente y la ejecución de CrewAI."""
    with (
        patch("src.agents.strategic_writer.build_writer"),
        patch("src.agents.strategic_writer.build_writing_task"),
        patch("src.agents.strategic_writer.Crew") as crew_class,
    ):
        kickoff = crew_class.return_value.kickoff
        yield kickoff


def test_writer_preserves_references_and_pending_questions(
    brief, simulated_response
):
    evidence = Evidence(
        evidence_id="price_1",
        claim="Cuota mensual de 45 euros.",
        source_url="https://example.com/tarifas",
        limitations="Tarifa de prueba.",
    )
    research = ResearchResult(
        evidences=[evidence],
        unresolved_questions=["¿Dispone de ludoteca?"],
    )

    simulated_response.return_value = SimpleNamespace(
        pydantic=WritingOutput(
            sections=["Resultados\nCuota mensual de 45 euros."],
            claims=[
                WritingClaim(
                    text="Cuota mensual de 45 euros.",
                    kind="fact",
                    evidence_ids=["price_1"],
                )
            ],
        )
    )

    draft = run_writing(brief, research)

    assert draft.study_area == brief.study_area
    assert draft.claims[0].evidence_ids == ["price_1"]
    assert draft.sources == ["https://example.com/tarifas"]
    assert "Tarifa de prueba." in draft.limitations
    assert any(
        "¿Dispone de ludoteca?" in item
        for item in draft.limitations
    )
    simulated_response.assert_called_once()


def test_writer_rejects_invented_reference(brief, simulated_response):
    simulated_response.return_value = SimpleNamespace(
        pydantic=WritingOutput(
            sections=["Resultados\nAfirmación de prueba."],
            claims=[
                WritingClaim(
                    text="Afirmación de prueba.",
                    kind="fact",
                    evidence_ids=["invented_1"],
                )
            ],
        )
    )

    with pytest.raises(ValueError, match="invented_1"):
        run_writing(brief, ResearchResult())


def test_writer_rejects_fact_without_references(
    brief, simulated_response
):
    simulated_response.return_value = SimpleNamespace(
        pydantic=WritingOutput(
            sections=["Resultados\nAfirmación sin respaldo."],
            claims=[
                WritingClaim(
                    text="Afirmación sin respaldo.",
                    kind="fact",
                )
            ],
        )
    )

    with pytest.raises(ValueError, match="hecho sin referencias"):
        run_writing(brief, ResearchResult())


def test_writer_rejects_unstructured_response(
    brief, simulated_response
):
    simulated_response.return_value = SimpleNamespace(pydantic=None)

    with pytest.raises(ValueError, match="salida estructurada"):
        run_writing(brief, ResearchResult())