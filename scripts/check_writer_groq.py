"""Comprobación manual: muestra guardada + cálculo hipotético + revisión."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path.cwd()))

from src.agents.strategic_writer import _writing_task_content
from src.agents.writer_payload import partition_writer_research
from src.agents.writer_budget import WRITER_TASK_TOKEN_LIMIT, count_writer_tokens
from src.agents.writer_llm import build_writer_llm
from src.analysis.scenarios import create_economic_scenario
from src.analysis.economic_calculations import create_break_even_calculation
from src.analysis.calculation_adapter import metric_from_break_even
from src.graph.review_routes import choose_review_route_for_context
from src.reporting.report_builder import build_report
from src.review.quality_checks import run_basic_review
from src.schemas import ResearchBrief, ResearchResult, Competitor

data = json.loads(Path("data/processed/competitor_registry.json").read_text(encoding="utf-8"))
competitors = [Competitor.model_validate(c) for c in data["competitors"]]
sample = [c for c in competitors if "gimnas" in " ".join(c.services).casefold()][:3]
assert len(sample) == 3
research = ResearchResult(
    competitors=sample, evidences=[e for c in sample for e in c.evidences],
    unresolved_questions=["Validar demanda y disposición a pagar.", "Verificar tarifas y servicios actuales."],
    search_performed=f"Lectura de tres registros del archivo preparado el {data['generated_at']}; sin consultas web ni actualización de datos en esta ejecución.",
    notes="Muestra administrativa limitada; no acredita operación comercial ni exhaustividad. Las secciones censales son identificadores separados.",
)
brief = ResearchBrief(business_type="gimnasio con ludoteca", location="Madrid", study_area="El Cañaveral", questions=["¿Qué datos existen y qué falta comprobar?"])
model = build_writer_llm().model

def fits(batch):
    content = _writing_task_content(brief, batch, None)
    return count_writer_tokens([{"role": "user", "content": content["description"] + "\n" + content["expected_output"]}], model) <= WRITER_TASK_TOKEN_LIMIT

batches = partition_writer_research(research, fits)
print("Lotes de la muestra:", len(batches), flush=True)
if "--plan-only" in sys.argv:
    large = research.model_copy(update={"competitors": competitors, "evidences": [e for c in competitors for e in c.evidences]})
    print("Lotes para los 18 registros:", len(partition_writer_research(large, fits)), flush=True)
    sys.exit(0)

scenario = create_economic_scenario("intermediate", 100, 50, 1000, 10, assumptions=["Parámetros económicos hipotéticos de prueba; no proceden del censo ni de tarifas reales."])
calculation = create_break_even_calculation(1000, 50, 10, limitations=["Escenario hipotético: no demuestra demanda ni viabilidad real."])
metrics = [metric_from_break_even(scenario, calculation)]
draft = build_report(brief, research, use_llm=True, calculated_metrics=metrics)
review = run_basic_review(draft, research, calculated_metrics=metrics)
route = choose_review_route_for_context(review, draft, research, revision_count=0, calculated_metrics=metrics)
numeric = [c for c in draft.claims if c.metric_id is not None]
assert len(draft.sections) == 11
assert len(numeric) == 1 and numeric[0].reported_value == 25
assert review.status == "pending_review", review.issues
assert route == "pending_review", route
print(json.dumps({"sections": len(draft.sections), "claims": len(draft.claims), "sources": len(draft.sources), "break_even_clients": numeric[0].reported_value, "review_status": review.status, "route": route, "issues": [i.code for i in review.issues]}, ensure_ascii=True), flush=True)
print("No se han aprobado ni exportado entregables.", flush=True)
