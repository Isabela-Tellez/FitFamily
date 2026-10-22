"""Pruebas de las referencias del borrador."""

from src.reporting.models import ReportClaim, ReportDraft
from src.reporting.report_builder import find_missing_evidence_ids
from src.schemas import Competitor, Evidence, ResearchResult


def test_existing_evidence_reference_is_accepted():
    """Una evidencia recibida no debe aparecer como inexistente."""
    evidence = Evidence(
        evidence_id="price_1",
        claim="Cuota mensual de prueba.",
    )
    draft = ReportDraft(
        title="Informe de prueba",
        study_area="El Cañaveral",
        claims=[
            ReportClaim(
                claim_id="claim_1",
                text="Cuota mensual de prueba.",
                kind="fact",
                evidence_ids=["price_1"],
            )
        ],
    )
    research = ResearchResult(evidences=[evidence])

    assert find_missing_evidence_ids(draft, research) == []


def test_missing_reference_is_reported_once():
    """Una referencia inexistente se devuelve sin duplicados."""
    draft = ReportDraft(
        title="Informe de prueba",
        study_area="El Cañaveral",
        claims=[
            ReportClaim(
                claim_id="claim_1",
                text="Afirmación de prueba.",
                kind="fact",
                evidence_ids=["missing_1", "missing_1"],
            )
        ],
    )

    assert find_missing_evidence_ids(
        draft,
        ResearchResult(),
    ) == ["missing_1"]


def test_evidence_inside_competitor_is_accepted():
    """También se buscan las evidencias dentro de los competidores."""
    evidence = Evidence(
        evidence_id="price_1",
        claim="Cuota mensual de prueba.",
    )
    competitor = Competitor(
        identifier="gym_1",
        evidences=[evidence],
    )
    research = ResearchResult(competitors=[competitor])
    draft = ReportDraft(
        title="Informe de prueba",
        study_area="El Cañaveral",
        claims=[
            ReportClaim(
                claim_id="claim_1",
                text="Cuota mensual de prueba.",
                kind="fact",
                evidence_ids=["price_1"],
            )
        ],
    )

    assert find_missing_evidence_ids(draft, research) == []

def test_build_report_returns_draft_with_valid_references():
    """El constructor genera un borrador con referencias existentes."""
    from src.reporting.report_builder import build_report
    from src.schemas import ResearchBrief

    brief = ResearchBrief(
        business_type="gimnasio con ludoteca",
        location="Madrid",
        study_area="El Cañaveral",
    )
    evidence = Evidence(
        evidence_id="price_1",
        claim="Cuota mensual publicada de 45 euros.",
        value=45,
        unit="euros",
        frequency="monthly",
        source_url="https://example.com/tarifas",
    )
    research = ResearchResult(evidences=[evidence])

    draft = build_report(brief, research)

    assert isinstance(draft, ReportDraft)
    assert draft.claims
    assert draft.claims[0].evidence_ids == ["price_1"]
    assert find_missing_evidence_ids(draft, research) == []


def test_build_report_rejects_missing_reference():
    """El constructor no devuelve un borrador con referencias inexistentes."""
    from unittest.mock import patch

    import pytest

    from src.reporting.report_builder import build_report
    from src.schemas import ResearchBrief

    brief = ResearchBrief(
        business_type="gimnasio con ludoteca",
        location="Madrid",
        study_area="El Cañaveral",
    )

    # Simulamos que el Writer produce una referencia incorrecta.
    invalid_draft = ReportDraft(
        title="Informe de prueba",
        study_area="El Cañaveral",
        claims=[
            ReportClaim(
                claim_id="claim_1",
                text="Afirmación de prueba.",
                kind="fact",
                evidence_ids=["missing_1"],
            )
        ],
    )

    with patch(
        "src.agents.writer_agent.WriterAgent.create_draft",
        return_value=invalid_draft,
    ):
        with pytest.raises(ValueError, match="missing_1"):
            build_report(brief, ResearchResult())