"""Cross-module contract: registry -> market analysis -> writer (Persona 1).

Uses the committed registry artifact, so it does not need network access and
does not invent prices, playrooms or search results.
"""

import json
from pathlib import Path

from src.agents.writer_agent import WriterAgent
from src.analysis.market_analysis import summarize_competitors
from src.schemas import Competitor, Evidence, ResearchBrief, ResearchResult
from src.tools.competitor_registry import to_dataframe

ARTIFACT = Path(__file__).resolve().parents[1] / "data" / "processed" / "competitor_registry.json"


def _artifact_competitors():
    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    return [Competitor(**raw) for raw in data["competitors"]]


def test_registry_dataframe_keeps_unknown_values_as_unknown():
    competitors = _artifact_competitors()
    frame = to_dataframe(competitors)

    assert {"gym_name", "monthly_price_eur", "has_playroom"} <= set(frame.columns)
    assert frame["has_playroom"].isna().all()
    assert frame["monthly_price_eur"].isna().all()

    summary = summarize_competitors(frame)
    assert summary["competitor_count"] == 18
    assert summary["known_price_count"] == 0
    assert summary["average_monthly_price_eur"] is None
    assert summary["playroom_yes_count"] == 0
    assert summary["playroom_no_count"] == 0
    assert summary["playroom_unknown_count"] == 18


def test_writer_accepts_the_registry_and_does_not_invent_missing_data():
    competitors = _artifact_competitors()
    official_evidences = [
        evidence for competitor in competitors for evidence in competitor.evidences
    ]
    # A failed search is traceable but must not become a source or a fact.
    rejected = Evidence(
        evidence_id="source_renta_media_deadbeef",
        claim="Fuente localizada para la variable 'renta media': sin fuente [rejected] La busqueda fallo: network down",
        source_url=None,
        limitations="La consulta no devolvio resultados o fallo la red.",
    )
    result = ResearchResult(
        evidences=official_evidences + [rejected],
        competitors=competitors,
        coverage_percentage=0.0,
        unresolved_questions=["renta media por barrio"],
        search_performed="Busqueda de fuentes fallida.",
    )
    brief = ResearchBrief(
        business_type="gimnasio con ludoteca",
        location="Madrid",
        study_area="El Cañaveral",
        questions=["renta media por barrio"],
    )

    draft = WriterAgent().create_draft(brief, result)

    assert draft.title
    assert draft.study_area == "El Cañaveral"
    assert draft.sources
    assert len(draft.sources) == len(set(draft.sources))
    assert all(source.startswith("https://") for source in draft.sources)
    assert all("datos.madrid.es" in source for source in draft.sources)

    text = "\n".join(draft.sections)
    assert "Nombre no disponible" in text
    assert "Tarifas: no disponibles." in text
    assert "0 euros" not in text
    assert "Precio: 0" not in text
    # The rejected evidence is a limitation, never a source.
    assert rejected.source_url not in draft.sources
    assert any("network down" in limitation or "fallo la red" in limitation
               for limitation in draft.limitations)
    # Licence states are presented as administrative, not as closure.
    assert any("no acredita" in limitation for limitation in draft.limitations)
    assert any("no disponible" in limitation.lower() for limitation in draft.limitations)


def test_competitor_model_roundtrip_keeps_none_fields():
    competitors = _artifact_competitors()
    raw = competitors[0].model_dump()
    restored = Competitor(**raw)
    assert restored == competitors[0]
    assert restored.latitude is None
    assert restored.has_playroom is None
    assert restored.tariffs == []
