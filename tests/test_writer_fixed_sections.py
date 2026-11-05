"""Regresión del PR #35: estructura final después de incorporar cálculos."""
import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.reporting.writing_models import parse_writing_output, writer_response_format
from src.reporting.models import ReportDraft
from src.reporting.templates import REPORT_SECTION_TITLES, validate_report_sections
from src.schemas import ResearchBrief, ResearchResult


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


def test_groq_strict_schema_requires_all_sections_and_claim_fields():
    fmt = writer_response_format("groq/openai/gpt-oss-120b")
    assert fmt["type"] == "json_schema" and fmt["json_schema"]["strict"] is True
    schema = fmt["json_schema"]["schema"]
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
    assert params["response_format"]["json_schema"]["strict"] is True


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
