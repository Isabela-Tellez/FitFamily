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