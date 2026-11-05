"""Demo MVP de FitFamily: flujo end-to-end sin red ni aprobacion humana real.

Genera investigacion ficticia, analisis, borrador, revision, aprobacion simulada
y exportacion Markdown/PDF/CSV en reports/mvp/.
"""
from datetime import datetime, timezone
from pathlib import Path

from src.automation.delivery import export_approved_report
from src.automation.exporter import calculate_draft_fingerprint
from src.automation.models import ApprovalRecord
from src.graph.review_routes import choose_review_route_for_context
from src.reporting.report_builder import build_report
from src.review.quality_checks import run_basic_review
from src.schemas import Evidence, ResearchBrief, ResearchResult
from src.analysis.scenarios import create_economic_scenario, evaluate_economic_scenario
from src.analysis.calculation_adapter import metric_from_break_even

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "reports" / "mvp"
OUTPUT.mkdir(parents=True, exist_ok=True)

brief = ResearchBrief(
    business_type="gimnasio con ludoteca",
    location="Madrid",
    study_area="Zona ficticia de prueba",
    questions=["Que tarifas estan documentadas?"],
    assumed_params={
        "expected_clients": 200,
        "monthly_fee": 40.0,
        "fixed_costs": 6000.0,
        "variable_cost_per_client": 10.0,
    },
)

evidence = Evidence(
    evidence_id="test_monthly_price",
    claim="La cuota ficticia de prueba es de 40 EUR al mes.",
    value=40,
    unit="EUR",
    frequency="monthly",
    source_url="https://example.com/tarifa-de-prueba",
    limitations="Dato ficticio utilizado solo en esta prueba.",
)
research = ResearchResult(
    evidences=[evidence],
    search_performed="Datos preparados para una prueba sin Internet.",
)

# Analisis: punto de equilibrio
params = brief.assumed_params
scenario = create_economic_scenario(
    scenario_type="intermediate",
    expected_clients=params["expected_clients"],
    monthly_fee=params["monthly_fee"],
    fixed_costs=params["fixed_costs"],
    variable_cost_per_client=params["variable_cost_per_client"],
    assumptions=["Parametros ficticios del MVP."],
)
calculations = evaluate_economic_scenario(
    scenario,
    evidence_ids=[evidence.evidence_id],
    limitations=["Proyeccion basada en parametros proporcionados."],
)
break_even_calc = next(c for c in calculations if c.calculation_type == "break_even")
metric = metric_from_break_even(
    scenario,
    break_even_calc,
    input_evidence_ids={},
)
metrics = [metric]

draft = build_report(brief, research, calculated_metrics=metrics)
fingerprint = calculate_draft_fingerprint(draft)
review = run_basic_review(draft, research, calculated_metrics=metrics)
route = choose_review_route_for_context(
    review, draft, research, revision_count=0, calculated_metrics=metrics
)

print("Draft:", draft.draft_id, "v", draft.version)
print("Review issues:", len(review.issues))
print("Route:", route)

if route != "pending_review":
    raise SystemExit("La revision no permite aprobar: " + str(route))

approval = ApprovalRecord(
    run_id="mvp-demo-run",
    draft_id=draft.draft_id,
    draft_version=draft.version,
    draft_fingerprint=fingerprint,
    approved=True,
    actions=("export_markdown", "export_pdf", "update_tracking_csv"),
    decided_at=datetime.now(timezone.utc),
)

result = export_approved_report(
    draft,
    approval,
    run_id=approval.run_id,
    output_dir=OUTPUT,
    csv_path=OUTPUT / "tracking.csv",
)

print("Complete:", result.complete)
print("Markdown:", result.markdown_path)
print("PDF:", result.pdf_path)
print("Tracking:", result.tracking_path)
if result.errors:
    print("Errors:", result.errors)
