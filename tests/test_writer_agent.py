from src.agents.writer_agent import WriterAgent
from src.reporting.models import ReportDraft
from src.schemas import ResearchBrief, ResearchResult


def test_create_draft_without_competitors():
    """Los datos ausentes deben quedar indicados en el informe."""
    brief = ResearchBrief(
        business_type="gimnasio con ludoteca",
        location="Madrid",
        study_area="El Cañaveral",
        questions=["¿Qué tarifas tienen los competidores?"],
    )

    research_result = ResearchResult(
        competitors=[],
        evidences=[],
        unresolved_questions=[
            "¿Qué tarifas tienen los competidores?"
        ],
    )

    draft = WriterAgent().create_draft(brief, research_result)

    assert isinstance(draft, ReportDraft)
    assert draft.study_area == "El Cañaveral"
    assert "gimnasio con ludoteca" in draft.title
    assert draft.sources == []

    text = "\n".join(draft.sections)
    assert "La investigación no ha aportado competidores" in text
    assert "¿Qué tarifas tienen los competidores?" in text

    assert any(
        "Pregunta pendiente:" in limitation
        for limitation in draft.limitations
    )


def test_create_draft_with_competitor():
    """Conserva la tarifa y su fuente sin duplicar enlaces."""
    from src.schemas import Competitor, Evidence

    brief = ResearchBrief(
        business_type="gimnasio con ludoteca",
        location="Madrid",
        study_area="El Cañaveral",
    )

    evidence = Evidence(
        evidence_id="test_price_1",
        claim="Cuota mensual de prueba: 45 euros.",
        value=45,
        unit="euros",
        frequency="monthly",
        source_url="https://example.com/tarifas",
        limitations="Datos ficticios para la prueba.",
    )

    competitor = Competitor(
        name="Gimnasio de prueba",
        location="El Cañaveral",
        tariffs=[
            {
                "value": 45,
                "unit": "euros",
                "frequency": "monthly",
                "condition": "Cuota de prueba.",
            }
        ],
        evidences=[evidence],
    )

    result = ResearchResult(
        competitors=[competitor],
        evidences=[evidence],
    )

    draft = WriterAgent().create_draft(brief, result)

    text = "\n".join(draft.sections)
    assert "Gimnasio de prueba" in text
    assert "45 euros; mensual" in text
    assert "https://example.com/tarifas" in text
    assert draft.sources == ["https://example.com/tarifas"]
    assert "Datos ficticios para la prueba." in draft.limitations

def test_draft_links_price_claim_to_evidence():
    """La afirmación de precio conserva la evidencia que la respalda."""
    from src.schemas import Competitor, Evidence

    brief = ResearchBrief(
        business_type="gimnasio con ludoteca",
        location="Madrid",
        study_area="El Cañaveral",
    )

    evidence = Evidence(
        evidence_id="price_gym_1",
        claim="El gimnasio publica una cuota mensual de 45 euros.",
        value=45,
        unit="euros",
        frequency="monthly",
        source_url="https://example.com/tarifas",
    )

    competitor = Competitor(
        identifier="gym_1",
        name="Gimnasio de prueba",
        evidences=[evidence],
    )

    result = ResearchResult(
        evidences=[evidence],
        competitors=[competitor],
    )

    draft = WriterAgent().create_draft(brief, result)

    matching_claims = [
        claim
        for claim in draft.claims
        if "price_gym_1" in claim.evidence_ids
    ]

    # La misma evidencia aparece en dos sitios, pero no debe duplicarse.
    assert len(matching_claims) == 1
    assert matching_claims[0].text == evidence.claim
    assert matching_claims[0].kind == "fact"

def test_price_without_source_does_not_create_claim():
    """Una tarifa sin fuente no genera una afirmación respaldada."""
    from src.schemas import Evidence

    brief = ResearchBrief(
        business_type="gimnasio con ludoteca",
        location="Madrid",
        study_area="El Cañaveral",
    )

    evidence = Evidence(
        evidence_id="price_without_source",
        claim="Cuota mensual de 45 euros sin fuente.",
        value=45,
        unit="euros",
        frequency="monthly",
        source_url=None,
    )

    result = ResearchResult(evidences=[evidence])

    draft = WriterAgent().create_draft(brief, result)

    assert draft.claims == []
    assert draft.sources == []
    assert not any(
        "Tarifas documentadas" in section
        for section in draft.sections
    )