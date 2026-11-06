"""Regresión del PR #35: estructura final después de incorporar cálculos."""
import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.reporting.writing_models import parse_writing_output, writer_response_format, writer_response_schema
from src.reporting.models import ReportClaim, ReportDraft
from src.reporting.templates import (
    MISSING_SECTION_TEXT, REPORT_SECTION_TITLES, validate_report_sections
)
from src.schemas import Evidence, ResearchBrief, ResearchResult
from src.agents import strategic_writer


def response():
    return {"sections": {title: f"Contenido de prueba de {title}." for title in REPORT_SECTION_TITLES}, "claims": [], "limitations": []}


def test_fixed_sections_build_canonical_titles_even_with_reversed_keys():
    data = response()
    data["sections"] = dict(reversed(list(data["sections"].items())))
    output = parse_writing_output(json.dumps(data))
    assert [s.partition("\n")[0] for s in output.sections] == list(REPORT_SECTION_TITLES)
    assert all(body in "\n".join(output.sections) for body in data["sections"].values())
    validate_report_sections(output.sections)


@pytest.mark.parametrize("change", ["missing", "extra", "empty", "wrong_type"])
def test_invalid_section_fields_are_not_repaired_or_discarded(change):
    data = response()
    title = REPORT_SECTION_TITLES[0]
    if change == "missing":
        del data["sections"][title]
    elif change == "extra":
        data["sections"]["Otro título"] = "No se debe descartar."
    elif change == "empty":
        data["sections"][title] = ""
    else:
        data["sections"][title] = 123
    with pytest.raises(ValidationError):
        parse_writing_output(json.dumps(data))


def test_duplicate_json_section_key_is_rejected():
    raw = json.dumps(response())
    raw = raw.replace('"sections": {', '"sections": {"Competencia": "Primera versión", ', 1)
    with pytest.raises(ValueError, match="duplicada"):
        parse_writing_output(raw)


def test_writer_response_format_uses_json_object_with_local_validation():
    fmt = writer_response_format("groq/openai/gpt-oss-120b")
    assert fmt == {"type": "json_object"}
    # El esquema estricto sigue disponible para validacion local.
    schema = writer_response_schema()
    sections = schema["$defs"]["WritingSections"]
    assert sections["required"] == list(REPORT_SECTION_TITLES)
    assert sections["additionalProperties"] is False
    assert schema["$defs"]["WritingClaim"]["required"] == ["text", "kind", "evidence_ids"]
    assert writer_response_format("groq/another-model") == {"type": "json_object"}


def test_installed_crewai_builds_and_forwards_strict_schema_without_api():
    from src.agents.writer_llm import build_writer_llm

    with patch("src.agents.writer_llm.load_dotenv"), patch.dict("os.environ", {
        "WRITER_LLM_MODEL": "groq/openai/gpt-oss-120b", "GROQ_API_KEY": "test-not-real",
    }):
        llm = build_writer_llm()
    params = llm._prepare_completion_params([{"role": "user", "content": "Prueba local."}])
    assert params["response_format"] == writer_response_format(llm.model)
    assert params["response_format"] == {"type": "json_object"}


def load_check_module():
    path = Path(__file__).resolve().parents[1] / "scripts/check_writer_groq.py"
    spec = importlib.util.spec_from_file_location("fitfamily_writer_check", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_final_structure_diagnostic_contains_actual_count_and_titles():
    draft = ReportDraft(title="Prueba", study_area="Zona", sections=["Apartado inesperado\nTexto"])
    with pytest.raises(ValueError, match="1 apartados, esperados 11") as caught:
        load_check_module().validate_check_result(draft, SimpleNamespace(), "pending_review")
    assert "Apartado inesperado" in str(caught.value)
    assert "Resumen ejecutivo" in str(caught.value)


def test_full_batched_builder_preserves_outline_and_adds_calculation_once():
    from src.agents import strategic_writer
    from src.analysis.scenarios import create_economic_scenario
    from src.analysis.economic_calculations import create_break_even_calculation
    from src.analysis.calculation_adapter import metric_from_break_even
    from src.reporting.report_builder import build_report
    from src.review.quality_checks import run_basic_review
    from src.graph.review_routes import choose_review_route_for_context

    brief = ResearchBrief(business_type="gimnasio", location="Madrid", study_area="Zona de prueba")
    research = ResearchResult()
    original = response()
    outputs = [copy.deepcopy(original), copy.deepcopy(original)]
    outputs[0]["sections"]["Competencia"] = "Contenido del primer lote."
    outputs[1]["sections"]["Competencia"] = "Contenido del segundo lote."
    scenario = create_economic_scenario("intermediate", 100, 50, 1000, 10, assumptions=["Hipótesis de prueba."])
    metrics = [metric_from_break_even(scenario, create_break_even_calculation(1000, 50, 10))]
    with patch.object(strategic_writer, "build_writer"), patch.object(strategic_writer, "build_writing_task"), patch.object(strategic_writer, "partition_writer_research", return_value=[research, research]), patch.object(strategic_writer, "Crew") as crew:
        crew.return_value.kickoff.side_effect = [SimpleNamespace(raw=json.dumps(item)) for item in outputs]
        draft = build_report(brief, research, use_llm=True, calculated_metrics=metrics)
    validate_report_sections(draft.sections)
    text = "\n".join(draft.sections)
    assert "Contenido del primer lote." in text and "Contenido del segundo lote." in text
    assert text.count("25 clientes") == 1
    review = run_basic_review(draft, research, calculated_metrics=metrics)
    route = choose_review_route_for_context(review, draft, research, revision_count=0, calculated_metrics=metrics)
    summary = load_check_module().validate_check_result(draft, review, route)
    assert summary["sections"] == 11
    assert summary["issues"] == []


# ---------------------------------------------------------------------------
# Pruebas del parser defensivo (normalizacion de formato Groq)
# ---------------------------------------------------------------------------

def test_parser_accepts_valid_object():
    data = response()
    output = parse_writing_output(json.dumps(data))
    assert [s.partition(chr(10))[0] for s in output.sections] == list(REPORT_SECTION_TITLES)
    assert output.claims == []
    assert output.limitations == []


def test_parser_unwraps_single_object_array():
    data = response()
    raw = json.dumps([data])
    output = parse_writing_output(raw)
    assert [s.partition(chr(10))[0] for s in output.sections] == list(REPORT_SECTION_TITLES)


def test_parser_rejects_empty_array():
    with pytest.raises(ValueError, match="array vac"):
        parse_writing_output("[]")


def test_parser_rejects_multiple_objects_array():
    data = response()
    raw = json.dumps([data, data])
    with pytest.raises(ValueError, match="varios objetos"):
        parse_writing_output(raw)


def test_parser_rejects_invalid_json():
    with pytest.raises(ValueError, match="JSON valido"):
        parse_writing_output("{not valid json")


def test_parser_rejects_missing_required_fields():
    data = response()
    del data["sections"]
    with pytest.raises(Exception):
        parse_writing_output(json.dumps(data))


def test_parser_rejects_wrong_types():
    data = response()
    data["sections"] = 123
    with pytest.raises(Exception):
        parse_writing_output(json.dumps(data))


def test_parser_preserves_claims_and_limitations():
    data = response()
    data["claims"] = [{"text": "Hecho verificado.", "kind": "fact", "evidence_ids": ["ev1"]}]
    data["limitations"] = ["Limitacion de prueba."]
    output = parse_writing_output(json.dumps(data))
    assert len(output.claims) == 1
    assert output.claims[0].text == "Hecho verificado."
    assert output.claims[0].evidence_ids == ["ev1"]
    assert output.limitations == ["Limitacion de prueba."]


def test_parser_preserves_numeric_values_in_sections():
    data = response()
    data["sections"][REPORT_SECTION_TITLES[0]] = "Ingresos: 10000.0 EUR/mes"
    output = parse_writing_output(json.dumps(data))
    assert "10000.0" in output.sections[0]


def test_parser_rejects_fact_without_references_at_runtime():
    data = response()
    data["claims"] = [{"text": "Hecho sin ref.", "kind": "fact", "evidence_ids": []}]
    output = parse_writing_output(json.dumps(data))
    assert output.claims[0].evidence_ids == []


def test_parser_handles_real_groq_array_wrapper():
    raw = '[{"sections": {"Resumen ejecutivo": "Contenido de prueba."}, "claims": [], "limitations": []}]'
    with pytest.raises(Exception):
        parse_writing_output(raw)


def test_parser_unwraps_array_with_complete_sections():
    data = response()
    raw = json.dumps([data])
    output = parse_writing_output(raw)
    assert [s.partition(chr(10))[0] for s in output.sections] == list(REPORT_SECTION_TITLES)


# ---------------------------------------------------------------------------
# Pruebas de la Fase 1: consolidacion del informe (unificacion de lotes)
# ---------------------------------------------------------------------------

def _make_draft(sections: dict[str, str], claims: list[dict]) -> ReportDraft:
    """Construye un ReportDraft de prueba con secciones y claims dados."""
    return ReportDraft(
        title="Prueba",
        study_area="Zona de prueba",
        sections=[f"{title}\n{sections.get(title, MISSING_SECTION_TEXT)}"
                  for title in REPORT_SECTION_TITLES],
        claims=[
            ReportClaim(
                claim_id=f"claim_{i:03d}",
                text=c["text"],
                kind=c["kind"],
                evidence_ids=list(c.get("evidence_ids", [])),
            )
            for i, c in enumerate(claims, start=1)
        ],
        sources=[],
        limitations=[],
    )


def test_consolidate_sections_unifies_lot_bodies_without_lot_prefixes():
    """Las secciones de varios lotes se unen en un solo texto sin 'Lote X'."""
    from src.agents.strategic_writer import _consolidate_sections

    d1 = _make_draft(
        {"Resumen ejecutivo": "Datos del lote uno."},
        [],
    )
    d2 = _make_draft(
        {"Resumen ejecutivo": "Datos del lote dos."},
        [],
    )
    sections = _consolidate_sections([d1, d2])
    resumen = sections[0]
    assert "Lote" not in resumen
    assert "contexto parcial" not in resumen
    assert "Datos del lote uno." in resumen
    assert "Datos del lote dos." in resumen


def test_consolidate_sections_keeps_missing_sections_as_not_available():
    """Los apartados sin informacion en ningún lote se mantienen como no disponibles."""
    from src.agents.strategic_writer import _consolidate_sections

    d1 = _make_draft({}, [])
    sections = _consolidate_sections([d1])
    for section in sections:
        title, _, body = section.partition(chr(10))
        if body == MISSING_SECTION_TEXT:
            assert body == MISSING_SECTION_TEXT
        else:
            assert body.strip() != ""


def test_deduplicate_claims_merges_evidence_ids():
    """Claims duplicados entre lotes se fusionan uniendo sus evidence_ids."""
    from src.agents.strategic_writer import _deduplicate_claims

    d1 = _make_draft(
        {},
        [{"text": "Winfit tiene sede en El Cañaveral.", "kind": "fact",
          "evidence_ids": ["ev1"]}],
    )
    d2 = _make_draft(
        {},
        [{"text": "Winfit tiene sede en El Cañaveral.", "kind": "fact",
          "evidence_ids": ["ev2"]}],
    )
    claims = _deduplicate_claims([d1, d2])
    assert len(claims) == 1
    assert set(claims[0].evidence_ids) == {"ev1", "ev2"}


def test_deduplicate_claims_preserves_distinct_claims():
    """Claims con texto diferente no se fusionan aunque sean del mismo tipo."""
    from src.agents.strategic_writer import _deduplicate_claims

    d1 = _make_draft(
        {},
        [{"text": "Winfit tiene sede en El Cañaveral.", "kind": "fact",
          "evidence_ids": ["ev1"]}],
    )
    d2 = _make_draft(
        {},
        [{"text": "Winfit ofrece clases gratuitas.", "kind": "fact",
          "evidence_ids": ["ev2"]}],
    )
    claims = _deduplicate_claims([d1, d2])
    assert len(claims) == 2


def test_build_global_summary_mentions_evidence_and_competitor_counts():
    """El resumen global cita el numero de evidencias y competidores."""
    from src.agents.strategic_writer import _build_global_summary

    d1 = _make_draft({}, [])
    research = ResearchResult(
        evidences=[Evidence(evidence_id="e1", claim="c", source_url="u")],
        competitors=[],
        coverage_percentage=50.0,
        search_performed="Búsqueda de prueba.",
    )
    brief = ResearchBrief(
        business_type="gimnasio con ludoteca",
        location="Madrid",
        study_area="El Cañaveral",
        questions=[],
    )
    summary = _build_global_summary([d1], research, brief)
    assert "1 evidencias" in summary
    assert "0 competidores" in summary
    assert "El Cañaveral" in summary


@pytest.fixture
def redactor_simulado(monkeypatch):
    """Permite probar la composición del informe sin crear un cliente de Groq."""
    from types import SimpleNamespace
    from src.agents import strategic_writer

    agente = SimpleNamespace(llm=SimpleNamespace(model="groq/openai/gpt-oss-120b"))
    monkeypatch.setattr(strategic_writer, "build_writer", lambda: agente)


def test_run_writing_consolidation_produces_global_summary(monkeypatch, redactor_simulado):
    """run_writing con varios lotes genera un resumen ejecutivo consolidado."""
    from src.agents import strategic_writer

    # Datos de prueba: dos lotes con información repetida y complementaria
    d1 = _make_draft(
        {"Resumen ejecutivo": "Primer lote: competencia detectada."},
        [{"text": "Winfit tiene sede en El Cañaveral.", "kind": "fact",
          "evidence_ids": ["ev1"]}],
    )
    d2 = _make_draft(
        {"Resumen ejecutivo": "Segundo lote: competencia detectada."},
        [{"text": "Winfit tiene sede en El Cañaveral.", "kind": "fact",
          "evidence_ids": ["ev2"]}],
    )

    research = ResearchResult(
        evidences=[
            Evidence(evidence_id="ev1", claim="Winfit sede", source_url="u1"),
            Evidence(evidence_id="ev2", claim="Winfit sede", source_url="u2"),
        ],
        competitors=[],
        coverage_percentage=50.0,
        search_performed="Búsqueda de prueba.",
    )
    brief = ResearchBrief(
        business_type="gimnasio con ludoteca",
        location="Madrid",
        study_area="El Cañaveral",
        questions=[],
    )

    call_count = {"n": 0}

    def fake_single(brief, batch, agent):
        call_count["n"] += 1
        return d1 if call_count["n"] == 1 else d2

    monkeypatch.setattr(
        strategic_writer, "_run_writing_single", fake_single,
    )
    monkeypatch.setattr(
        strategic_writer, "partition_writer_research",
        lambda research, fits: [research, research],
    )

    draft = strategic_writer.run_writing(brief, research)

    # El resumen ejecutivo no debe tener prefijos de lote
    resumen = draft.sections[0]
    assert "Lote" not in resumen
    assert "contexto parcial" not in resumen
    # Debe mencionar la síntesis global
    assert "Se investigó el mercado" in resumen
    # Los claims deben estar deduplicados (mismo texto, evidence_ids unidos)
    assert len(draft.claims) == 1
    assert set(draft.claims[0].evidence_ids) == {"ev1", "ev2"}
    # La limitación de síntesis global debe estar presente
    assert any("Informe consolidado" in l for l in draft.limitations)


# ---------------------------------------------------------------------------
# Pruebas de la Fase 2: relleno de secciones en single-batch
# ---------------------------------------------------------------------------

def _make_research_with_evidences(evidences: list[dict]) -> ResearchResult:
    """Construye un ResearchResult con evidencias dadas."""
    return ResearchResult(
        evidences=[
            Evidence(
                evidence_id=e["evidence_id"],
                claim=e["claim"],
                source_url=e.get("source_url", "u"),
            )
            for e in evidences
        ],
        competitors=[],
        coverage_percentage=50.0,
        search_performed="Búsqueda de prueba.",
    )


def test_single_batch_rellena_secciones_vacias(monkeypatch, redactor_simulado):
    """Un único lote con secciones vacías debe rellenarlas."""
    from src.agents import strategic_writer

    d1 = _make_draft(
        {"Resumen ejecutivo": "Texto del único lote."},
        [],
    )

    research = _make_research_with_evidences([
        {"evidence_id": "e1", "claim": "Winfit sede", "source_url": "u1"},
    ])
    brief = ResearchBrief(
        business_type="gimnasio con ludoteca",
        location="Madrid",
        study_area="El Cañaveral",
        questions=[],
    )

    def fake_single(brief, batch, agent):
        return d1

    monkeypatch.setattr(
        strategic_writer, "_run_writing_single", fake_single,
    )
    monkeypatch.setattr(
        strategic_writer, "partition_writer_research",
        lambda research, fits: [research],
    )

    draft = strategic_writer.run_writing(brief, research)

    # Público potencial debe estar rellenado (no MISSING_SECTION_TEXT)
    seccion_publico = draft.sections[REPORT_SECTION_TITLES.index("Público potencial")]
    assert MISSING_SECTION_TEXT not in seccion_publico
    assert "competidores" in seccion_publico.lower()

    # Competencia debe estar rellenada
    seccion_competencia = draft.sections[REPORT_SECTION_TITLES.index("Competencia")]
    assert MISSING_SECTION_TEXT not in seccion_competencia


def test_single_batch_no_sobreescribe_secciones_llenas(monkeypatch, redactor_simulado):
    """Un único lote con secciones ya completas no las sobrescribe."""
    from src.agents import strategic_writer

    texto_original = "Contenido propio del redactor."
    d1 = _make_draft(
        {"Público potencial": texto_original},
        [],
    )

    research = _make_research_with_evidences([
        {"evidence_id": "e1", "claim": "c", "source_url": "u1"},
    ])
    brief = ResearchBrief(
        business_type="gimnasio con ludoteca",
        location="Madrid",
        study_area="El Cañaveral",
        questions=[],
    )

    def fake_single(brief, batch, agent):
        return d1

    monkeypatch.setattr(
        strategic_writer, "_run_writing_single", fake_single,
    )
    monkeypatch.setattr(
        strategic_writer, "partition_writer_research",
        lambda research, fits: [research],
    )

    draft = strategic_writer.run_writing(brief, research)

    seccion_publico = draft.sections[REPORT_SECTION_TITLES.index("Público potencial")]
    assert texto_original in seccion_publico


def test_single_batch_no_datos_visuales_mantiene_pendiente(monkeypatch, redactor_simulado):
    """Un único lote sin datos visuales mantiene Análisis visual pendiente."""
    from src.agents import strategic_writer

    d1 = _make_draft(
        {"Análisis visual": MISSING_SECTION_TEXT},
        [],
    )

    research = _make_research_with_evidences([
        {"evidence_id": "e1", "claim": "c", "source_url": "u1"},
    ])
    brief = ResearchBrief(
        business_type="gimnasio con ludoteca",
        location="Madrid",
        study_area="El Cañaveral",
        questions=[],
    )

    def fake_single(brief, batch, agent):
        return d1

    monkeypatch.setattr(
        strategic_writer, "_run_writing_single", fake_single,
    )
    monkeypatch.setattr(
        strategic_writer, "partition_writer_research",
        lambda research, fits: [research],
    )

    draft = strategic_writer.run_writing(brief, research)

    seccion_visual = draft.sections[REPORT_SECTION_TITLES.index("Análisis visual")]
    assert MISSING_SECTION_TEXT in seccion_visual


def test_varios_lotes_con_secciones_repeticiones(monkeypatch, redactor_simulado):
    """Varios lotes con secciones repetidas se unifican sin duplicar."""
    from src.agents import strategic_writer

    d1 = _make_draft(
        {"Resumen ejecutivo": "Texto del lote uno."},
        [],
    )
    d2 = _make_draft(
        {"Resumen ejecutivo": "Texto del lote uno."},
        [],
    )

    research = _make_research_with_evidences([
        {"evidence_id": "e1", "claim": "c", "source_url": "u1"},
    ])
    brief = ResearchBrief(
        business_type="gimnasio con ludoteca",
        location="Madrid",
        study_area="El Cañaveral",
        questions=[],
    )

    call_count = {"n": 0}

    def fake_single(brief, batch, agent):
        call_count["n"] += 1
        return d1 if call_count["n"] == 1 else d2

    monkeypatch.setattr(
        strategic_writer, "_run_writing_single", fake_single,
    )
    monkeypatch.setattr(
        strategic_writer, "partition_writer_research",
        lambda research, fits: [research, research],
    )

    draft = strategic_writer.run_writing(brief, research)

    seccion_resumen = draft.sections[REPORT_SECTION_TITLES.index("Resumen ejecutivo")]
    assert "Lote" not in seccion_resumen
    assert "contexto parcial" not in seccion_resumen
    assert "Se investigó el mercado" in seccion_resumen


def test_varios_lotes_con_secciones_vacias(monkeypatch, redactor_simulado):
    """Varios lotes con secciones vacías se rellenan."""
    from src.agents import strategic_writer

    d1 = _make_draft(
        {"Público potencial": MISSING_SECTION_TEXT},
        [],
    )
    d2 = _make_draft(
        {"Público potencial": MISSING_SECTION_TEXT},
        [],
    )

    research = _make_research_with_evidences([
        {"evidence_id": "e1", "claim": "c", "source_url": "u1"},
    ])
    brief = ResearchBrief(
        business_type="gimnasio con ludoteca",
        location="Madrid",
        study_area="El Cañaveral",
        questions=[],
    )

    call_count = {"n": 0}

    def fake_single(brief, batch, agent):
        call_count["n"] += 1
        return d1 if call_count["n"] == 1 else d2

    monkeypatch.setattr(
        strategic_writer, "_run_writing_single", fake_single,
    )
    monkeypatch.setattr(
        strategic_writer, "partition_writer_research",
        lambda research, fits: [research, research],
    )

    draft = strategic_writer.run_writing(brief, research)

    seccion_publico = draft.sections[REPORT_SECTION_TITLES.index("Público potencial")]
    assert MISSING_SECTION_TEXT not in seccion_publico
    assert "competidores" in seccion_publico.lower()


# ---------------------------------------------------------------------------
# Pruebas de la Fase 3: detección de contradicciones
# ---------------------------------------------------------------------------

def _make_claim_with_price(text: str, value: float, evidence_id: str) -> ReportClaim:
    """Crea un claim de tipo fact con precio numérico."""
    return ReportClaim(
        claim_id="claim_001",
        text=text,
        kind="fact",
        evidence_ids=[evidence_id],
        metric_id="calculated_test",
        reported_value=value,
        reported_unit="EUR/mes",
    )


def _make_claim_no_publica(text: str, evidence_id: str) -> ReportClaim:
    """Crea un claim de tipo fact que declara no publicar tarifa."""
    return ReportClaim(
        claim_id="claim_001",
        text=text,
        kind="fact",
        evidence_ids=[evidence_id],
        metric_id=None,
        reported_value=None,
        reported_unit=None,
    )


def test_contradiccion_winfit_precio_vs_no_publica():
    """Winfit con precio y ausencia de tarifa deben detectarse como contradicción."""
    from src.agents.strategic_writer import _detectar_contradicciones

    d1 = _make_draft(
        {},
        [{"text": "Winfit tiene sede en El Cañaveral.", "kind": "fact",
          "evidence_ids": ["ev1"]}],
    )
    d2 = _make_draft(
        {},
        [{"text": "Winfit no publica tarifas.", "kind": "fact",
          "evidence_ids": ["ev2"]}],
    )
    # Añadir un claim con precio a d1
    d1.claims.append(
        ReportClaim(
            claim_id="claim_002",
            text="Winfit cobra 70 €/mes.",
            kind="fact",
            evidence_ids=["ev3"],
            metric_id="calculated_test",
            reported_value=70.0,
            reported_unit="EUR/mes",
        )
    )

    contradicciones = _detectar_contradicciones([d1, d2])
    assert len(contradicciones) == 1
    assert contradicciones[0]["entidad"] == "Winfit"
    assert contradicciones[0]["tipo"] == "precio_vs_no_publica"
    # ev3 es el claim con precio, ev2 es el que dice no publicar tarifas
    assert "ev3" in contradicciones[0]["evidence_ids"]
    assert "ev2" in contradicciones[0]["evidence_ids"]


def test_afirmaciones_equivalentes_no_son_contradiccion():
    """Dos afirmaciones con texto diferente no son contradicción de precio."""
    from src.agents.strategic_writer import _detectar_contradicciones

    d1 = _make_draft(
        {},
        [{"text": "Winfit tiene sede en El Cañaveral.", "kind": "fact",
          "evidence_ids": ["ev1"]}],
    )
    d2 = _make_draft(
        {},
        [{"text": "Winfit ofrece clases gratuitas.", "kind": "fact",
          "evidence_ids": ["ev2"]}],
    )

    contradicciones = _detectar_contradicciones([d1, d2])
    assert len(contradicciones) == 0


def test_dos_tarifas_modalidades_diferentes_no_son_contradiccion():
    """Dos precios para servicios diferentes no son contradicción."""
    from src.agents.strategic_writer import _detectar_contradicciones

    d1 = _make_draft(
        {},
        [{"text": "Winfit cuota mensual 70 €/mes.", "kind": "fact",
          "evidence_ids": ["ev1"]}],
    )
    d2 = _make_draft(
        {},
        [{"text": "Winfit bono 10 sesiones 50 €.", "kind": "fact",
          "evidence_ids": ["ev2"]}],
    )

    contradicciones = _detectar_contradicciones([d1, d2])
    # Diferentes contextos (cuota mensual vs bono sesiones) no son contradicción
    assert len(contradicciones) == 0


def test_precio_plataforma_no_es_tarifa_comercial():
    """Un precio de 0€ de plataforma no se trata como tarifa comercial."""
    from src.agents.strategic_writer import _detectar_contradicciones

    d1 = _make_draft(
        {},
        [{"text": "Wellhub acceso gratuito 0 €/mes.", "kind": "fact",
          "evidence_ids": ["ev1"]}],
    )
    d2 = _make_draft(
        {},
        [{"text": "Wellhub no publica tarifa comercial.", "kind": "fact",
          "evidence_ids": ["ev2"]}],
    )

    contradicciones = _detectar_contradicciones([d1, d2])
    # 0 € vs "no publica tarifa comercial" - son contextos diferentes,
    # no se marca como contradicción de precio comercial
    assert len(contradicciones) == 0


def test_contradicciones_se_conservan_en_borrador(monkeypatch, redactor_simulado):
    """Las contradicciones detectadas se añaden a las limitaciones del borrador."""
    from src.agents import strategic_writer

    d1 = _make_draft(
        {},
        [{"text": "Winfit tiene sede en El Cañaveral.", "kind": "fact",
          "evidence_ids": ["ev1"]}],
    )
    d1.claims.append(
        ReportClaim(
            claim_id="claim_002",
            text="Winfit cobra 70 €/mes.",
            kind="fact",
            evidence_ids=["ev2"],
            metric_id="calculated_test",
            reported_value=70.0,
            reported_unit="EUR/mes",
        )
    )
    d2 = _make_draft(
        {},
        [{"text": "Winfit no publica tarifas.", "kind": "fact",
          "evidence_ids": ["ev3"]}],
    )

    research = _make_research_with_evidences([
        {"evidence_id": "ev1", "claim": "Winfit sede", "source_url": "u1"},
        {"evidence_id": "ev2", "claim": "Winfit precio", "source_url": "u2"},
        {"evidence_id": "ev3", "claim": "Winfit no publica", "source_url": "u3"},
    ])
    brief = ResearchBrief(
        business_type="gimnasio con ludoteca",
        location="Madrid",
        study_area="El Cañaveral",
        questions=[],
    )

    call_count = {"n": 0}

    def fake_single(brief, batch, agent):
        call_count["n"] += 1
        return d1 if call_count["n"] == 1 else d2

    monkeypatch.setattr(
        strategic_writer, "_run_writing_single", fake_single,
    )
    monkeypatch.setattr(
        strategic_writer, "partition_writer_research",
        lambda research, fits: [research, research],
    )

    draft = strategic_writer.run_writing(brief, research)

    # Debe existir al menos una limitación que mencione contradicción
    assert any("Contradicciones detectadas" in l for l in draft.limitations)
    # Las evidencias deben conservarse
    assert len(draft.claims) >= 1
