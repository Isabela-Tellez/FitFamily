"""Demo MVP de FitFamily con datos reales de busqueda web (DuckDuckGo).

Deshabilita Tavily (clave placeholder) y usa ddgs. No requiere GROQ.
Genera investigacion real, analisis, borrador, revision y exportacion.
"""
import os
import crewai  # noqa: F401  (carga .env)

from datetime import datetime, timezone
from pathlib import Path

from src.automation.delivery import export_approved_report
from src.automation.exporter import calculate_draft_fingerprint
from src.automation.models import ApprovalRecord
from src.graph.review_routes import choose_review_route_for_context
from src.reporting.report_builder import build_report
from src.review.quality_checks import run_basic_review
from src.schemas import ResearchBrief, Evidence
from src.agents.researcher import run_research
from src.analysis.scenarios import create_economic_scenario, evaluate_economic_scenario
from src.analysis.calculation_adapter import metric_from_break_even

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "reports" / "mvp_real"
OUTPUT.mkdir(parents=True, exist_ok=True)

brief = ResearchBrief(
    business_type="gimnasio con ludoteca",
    location="Madrid",
    study_area="El Canaveral",
    questions=["Que competidores existen y que tarifas documentadas hay?"],
    assumed_params={
        "expected_clients": 200,
        "monthly_fee": 40.0,
        "fixed_costs": 6000.0,
        "variable_cost_per_client": 10.0,
    },
)

import asyncio
from src.mcp.client import connect_mcp, call_area_statistics
...
print("Ejecutando investigacion real (ddgs)...")
research = run_research(brief)
print("Evidencias:", len(research.evidences), "Competidores:", len(research.competitors))
print("Search:", research.search_performed)

# Datos municipales reales via MCP
print("Consultando MCP (indicadores de El Canaveral)...")
async def fetch_mcp():
    async with connect_mcp() as session:
        return await call_area_statistics(session, "El Canaveral", None)

mcp_result = asyncio.run(fetch_mcp())
source = mcp_result.get("source", "MCP local")
for key, info in mcp_result.get("results", {}).items():
    if info.get("verification_status") == "verified" and info.get("value") is not None:
        research.evidences.append(
            Evidence(
                evidence_id=f"mcp_{key}",
                claim=f"{key}: {info['value']} {info['unit']} ({info.get('reference_period','')})",
                value=info["value"],
                unit=info["unit"],
                source_url=info.get("source_url"),
                limitations=info.get("limitations", ""),
            )
        )
print("Evidencias tras MCP:", len(research.evidences))

params = brief.assumed_params
scenario = create_economic_scenario(
    scenario_type="intermediate",
    expected_clients=params["expected_clients"],
    monthly_fee=params["monthly_fee"],
    fixed_costs=params["fixed_costs"],
    variable_cost_per_client=params["variable_cost_per_client"],
    assumptions=["Parametros del MVP."],
)
calculations = evaluate_economic_scenario(scenario, limitations=["Proyeccion basada en parametros."])
break_even_calc = next(c for c in calculations if c.calculation_type == "break_even")
metric = metric_from_break_even(scenario, break_even_calc, input_evidence_ids={})
metrics = [metric]

draft = build_report(brief, research, calculated_metrics=metrics)
fingerprint = calculate_draft_fingerprint(draft)
review = run_basic_review(draft, research, calculated_metrics=metrics)
route = choose_review_route_for_context(review, draft, research, revision_count=0, calculated_metrics=metrics)

print("Draft:", draft.draft_id, "v", draft.version)
print("Review issues:", len(review.issues))
print("Route:", route)
for i in review.issues:
    print(" -", i.code, "|", i.message)

if route != "pending_review":
    raise SystemExit("La revision no permite aprobar: " + str(route))

approval = ApprovalRecord(
    run_id="mvp-real-run",
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
