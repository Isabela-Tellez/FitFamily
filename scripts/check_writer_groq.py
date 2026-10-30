"""Comprobación manual sin aprobar ni exportar: muestra + cálculo + revisión."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from src.agents.strategic_writer import _writing_task_content, count_writing_task_tokens
from src.agents.writer_payload import partition_writer_research
from src.agents.writer_budget import WRITER_TASK_TOKEN_LIMIT
from src.analysis.scenarios import create_economic_scenario
from src.analysis.economic_calculations import create_break_even_calculation
from src.analysis.calculation_adapter import metric_from_break_even
from src.graph.review_routes import choose_review_route_for_context
from src.reporting.report_builder import build_report
from src.reporting.templates import REPORT_SECTION_TITLES, validate_report_sections
from src.review.quality_checks import run_basic_review
from src.schemas import ResearchBrief, ResearchResult, Competitor


def validate_check_result(draft, review, route):
    """Diagnóstico explícito, también con python -O; no repara el borrador."""
    try:
        validate_report_sections(draft.sections)
    except ValueError as exc:
        raise ValueError(
            f"Estructura final incorrecta tras build_report: "
            f"{len(draft.sections)} apartados, esperados {len(REPORT_SECTION_TITLES)}. "
            f"{exc}"
        ) from exc
    numeric = [c for c in draft.claims if c.metric_id is not None]
    if len(numeric) != 1 or numeric[0].reported_value != 25:
        raise ValueError("La comprobación esperaba una única métrica hipotética de 25 clientes.")
    if review.status != "pending_review" or route != "pending_review":
        raise ValueError(f"Revisión: {review.status}; ruta: {route}; incidencias: {review.issues!r}")
    return {
        "sections": len(draft.sections),
        "section_titles": [s.strip().partition("\n")[0] for s in draft.sections],
        "claims": len(draft.claims), "sources": len(draft.sources),
        "break_even_clients": numeric[0].reported_value,
        "review_status": review.status, "route": route,
        "issues": [i.code for i in review.issues],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-only", action="store_true", help="Solo calcula lotes, sin clave ni peticiones al LLM.")
    args = parser.parse_args(argv)
    data = json.loads((ROOT / "data/processed/competitor_registry.json").read_text(encoding="utf-8"))
    competitors = [Competitor.model_validate(c) for c in data["competitors"]]
    sample = [c for c in competitors if "gimnas" in " ".join(c.services).casefold()][:3]
    if len(sample) != 3:
        raise ValueError("La muestra de comprobación requiere tres registros de gimnasio.")
    research = ResearchResult(
        competitors=sample, evidences=[e for c in sample for e in c.evidences],
        unresolved_questions=["Validar demanda y disposición a pagar.", "Verificar tarifas y servicios actuales."],
        search_performed=f"Lectura de tres registros del archivo preparado el {data['generated_at']}; sin consultas web ni actualización de datos en esta ejecución.",
        notes="Muestra administrativa limitada; no acredita operación comercial ni exhaustividad. Las secciones censales son identificadores separados.",
    )
    brief = ResearchBrief(business_type="gimnasio con ludoteca", location="Madrid", study_area="El Cañaveral", questions=["¿Qué datos existen y qué falta comprobar?"])
    load_dotenv(ROOT / ".env", override=False)
    model = os.getenv("WRITER_LLM_MODEL", "groq/openai/gpt-oss-120b").strip()

    def fits(batch):
        return count_writing_task_tokens(_writing_task_content(brief, batch, None), model) <= WRITER_TASK_TOKEN_LIMIT

    print("Lotes de la muestra:", len(partition_writer_research(research, fits)), flush=True)
    if args.plan_only:
        large = research.model_copy(update={"competitors": competitors, "evidences": [e for c in competitors for e in c.evidences]})
        print(f"Lotes para los {len(competitors)} registros:", len(partition_writer_research(large, fits)), flush=True)
        return

    scenario = create_economic_scenario("intermediate", 100, 50, 1000, 10, assumptions=["Parámetros económicos hipotéticos de prueba; no proceden del censo ni de tarifas reales."])
    calculation = create_break_even_calculation(1000, 50, 10, limitations=["Escenario hipotético: no demuestra demanda ni viabilidad real."])
    metrics = [metric_from_break_even(scenario, calculation)]
    draft = build_report(brief, research, use_llm=True, calculated_metrics=metrics)
    review = run_basic_review(draft, research, calculated_metrics=metrics)
    route = choose_review_route_for_context(review, draft, research, revision_count=0, calculated_metrics=metrics)
    print(json.dumps(validate_check_result(draft, review, route), ensure_ascii=True), flush=True)
    print("No se han aprobado ni exportado entregables.", flush=True)


if __name__ == "__main__":
    main()
