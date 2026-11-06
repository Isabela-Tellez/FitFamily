import sys,json,subprocess
from pathlib import Path
from datetime import datetime,timezone
from dotenv import load_dotenv
repo=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(repo))
load_dotenv(repo/".env",override=False)
from src.schemas import Competitor,ResearchBrief,ResearchResult
from src.analysis.scenarios import create_economic_scenario,evaluate_economic_scenario
from src.analysis.calculation_adapter import metric_from_scenario_calculation
from src.reporting.report_builder import build_report
from src.reporting.pdf_renderer import render_report_pdf
from src.reporting.markdown_renderer import render_report_markdown
from src.review.quality_checks import run_basic_review
from src.graph.review_routes import choose_review_route_for_context
out=repo/"outputs/demo_groq"
out.mkdir(parents=True,exist_ok=True)
raw=json.loads((repo/"data/processed/competitor_registry.json").read_text(encoding="utf-8"))
competitors=[Competitor.model_validate(x) for x in raw["competitors"] if any("gimnas" in s.lower() for s in x["services"])][:3]
research=ResearchResult(competitors=competitors,evidences=[e for c in competitors for e in c.evidences],unresolved_questions=["Validar demanda y disposición a pagar.","Contrastar precios y servicios actuales."],search_performed="Muestra municipal guardada; sin nuevas búsquedas web.",notes="Muestra limitada de tres registros administrativos; no acredita operación comercial actual.")
metrics=[]
for kind,clients in (("conservative",10),("intermediate",100),("optimistic",150)):
    s=create_economic_scenario(kind,clients,50,1000,10,assumptions=["Escenario ficticio para comprobar la integración del informe."])
    metrics.extend(metric_from_scenario_calculation(s,c) for c in evaluate_economic_scenario(s))
brief=ResearchBrief(business_type="gimnasio con ludoteca",location="Madrid",study_area="El Cañaveral",questions=["¿Qué oferta consta en la muestra municipal?","¿Qué información falta para evaluar la demanda?"])
try:
    draft=build_report(brief,research,use_llm=True,calculated_metrics=metrics)
    review=run_basic_review(draft,research,calculated_metrics=metrics)
    route=choose_review_route_for_context(review,draft,research,0,calculated_metrics=metrics)
    (out/"informe-groq.md").write_text(render_report_markdown(draft),encoding="utf-8")
    (out/"informe-groq.pdf").write_bytes(render_report_pdf(draft))
    result={"timestamp":datetime.now(timezone.utc).isoformat(),"sections":len(draft.sections),"claims":len(draft.claims),"competitors":len(competitors),"metrics":len(metrics),"route":route,"issues":[i.code for i in review.issues],"web_search":False,"approved":False}
except Exception as exc:
    result={"error_type":type(exc).__name__,"message":str(exc)[:500]}
(out/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(result,ensure_ascii=True))

