import os, sys, time, json, tempfile
from pathlib import Path

os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["LANGCHAIN_TRACING_V2"] = "false"

TMP = Path(tempfile.mkdtemp(prefix="fitfamily_e2e_"))
os.environ["FITFAMILY_DATA_DIR"] = str(TMP / "data")
os.environ["FITFAMILY_OUTPUT_DIR"] = str(TMP / "outputs" / "reports")
os.environ["FITFAMILY_CHECKPOINTS_DB"] = str(TMP / "data" / "checkpoints.sqlite")
os.environ["FITFAMILY_EVENTS_DB"] = str(TMP / "data" / "fitfamily_events.sqlite")
os.environ["FITFAMILY_TRACKING_CSV"] = str(TMP / "outputs" / "tracking.csv")

from dotenv import load_dotenv
load_dotenv(r"C:\Users\JUAN\Desktop\Proyectos\FitFamily_PR40_PR41_Integration\.env", override=False)

WORKTREE = Path(r"C:\Users\JUAN\Desktop\Proyectos\FitFamily_PR40_PR41_Integration")
os.chdir(WORKTREE)
if str(WORKTREE) not in sys.path:
    sys.path.insert(0, str(WORKTREE))

from src.ui.studio.services import provider_status
ps = provider_status()
print("PROVIDER STATUS:", ps)
assert ps["llm_ready"] == "yes", "GROQ no disponible"

from src.config import settings
from src.graph.persistence import open_checkpointer
from src.graph.workflow import build_workflow
from src.runtime import controller
from src.runtime.events import read_events

def _normalize(result):
    if isinstance(result, dict):
        return result
    v = getattr(result, "values", None)
    if isinstance(v, dict):
        return v
    return result

RUN_ID = "fitfamily-e2e-demo-001"
BRIEF = {
    "business_type": "gimnasio con ludoteca",
    "location": "Madrid",
    "study_area": "El Cañaveral",
    "questions": [
        "¿Qué competidores ofrecen servicios deportivos similares?",
        "¿Qué tarifas y servicios publican?",
        "¿Qué información oficial existe sobre población y hogares?",
    ],
    "assumed_params": {
        "expected_clients": 250,
        "monthly_fee": 40.0,
        "fixed_costs": 6000.0,
        "variable_cost_per_client": 10.0,
    },
    "search_limits": {"max_results": 6},
}

report = {"tmp": str(TMP), "run_id": RUN_ID, "stages": {}}

print("\n=== 1. INICIAR EJECUCION (start_run) ===")
t0 = time.time()
with open_checkpointer(settings.checkpoints_db_path) as ck:
    graph = build_workflow(checkpointer=ck, events_db_path=settings.events_db_path)
    result = controller.start_run(graph, RUN_ID, BRIEF)
    state = _normalize(result)
    report["stages"]["start"] = {"status": state.get("status"), "seconds": round(time.time()-t0,1)}
    print("STATUS:", state.get("status"))
    research = state.get("research_result") or {}
    print("RESEARCH evidences:", len(research.get("evidences", [])))
    print("RESEARCH competitors:", len(research.get("competitors", [])))
    print("RESEARCH search_performed:", research.get("search_performed", "")[:400])
    analysis = state.get("analysis_result") or {}
    metrics = analysis.get("calculated_metrics", [])
    print("METRICS count:", len(metrics))
    for m in metrics:
        print("  ", m.get("metric_id"), "=", m.get("value"), m.get("unit"))
    draft = state.get("report_draft") or {}
    print("DRAFT title:", draft.get("title"))
    print("DRAFT sections:", len(draft.get("sections", [])))
    print("DRAFT claims:", len(draft.get("claims", [])))
    review = state.get("review_result") or {}
    print("REVIEW status:", review.get("status"))
    print("REVIEW issues:", len(review.get("issues", [])))
    for iss in review.get("issues", []):
        print("   ", iss.get("severity"), iss.get("code"), "-", iss.get("message", "")[:80])
    events = read_events(RUN_ID, db_path=settings.events_db_path)
    print("EVENTS count:", len(events))
    print("LAST 10 events:")
    for e in events[-10:]:
        print("   ", e["stage"], "|", e["message"][:90])
    report["stages"]["research_evidences"] = len(research.get("evidences", []))
    report["stages"]["research_competitors"] = len(research.get("competitors", []))
    report["stages"]["metrics"] = {m.get("metric_id"): m.get("value") for m in metrics}
    report["stages"]["draft_sections"] = len(draft.get("sections", []))
    report["stages"]["draft_claims"] = len(draft.get("claims", []))
    report["stages"]["review_status"] = review.get("status")
    report["stages"]["review_issues"] = len(review.get("issues", []))
    report["stages"]["events"] = len(events)

    assert state.get("status") == "awaiting_approval", f"Expected awaiting_approval, got {state.get('status')}"

    print("\n=== 2. APROBACION HUMANA (resume_run) ===")
    t1 = time.time()
    rv_id = state.get("report_version_id")
    print("report_version_id:", rv_id)
    delivery = controller.resume_run(graph, RUN_ID, {
        "decision": "approved",
        "report_version_id": rv_id,
        "actions": ["export_markdown", "export_pdf", "update_tracking_csv"],
    })
    report["stages"]["approval_seconds"] = round(time.time()-t1,1)
    print("DELIVERY:", delivery)
    snap = controller.load_run(graph, RUN_ID)
    state2 = _normalize(snap)
    report["stages"]["post_approval_status"] = state2.get("status")
    print("POST-APPROVAL STATUS:", state2.get("status"))
    dr = state2.get("delivery_result")
    print("DELIVERY_RESULT:", dr)
    if dr:
        print("  requested:", dr.get("requested_actions"))
        print("  completed:", dr.get("completed_actions"))
        print("  failed:", dr.get("failed_actions"))
        print("  errors:", dr.get("errors"))
        print("  markdown_path:", dr.get("markdown_path"))
        print("  pdf_path:", dr.get("pdf_path"))
        print("  tracking_path:", dr.get("tracking_path"))
        report["stages"]["delivery"] = {
            "requested": list(dr.get("requested_actions", [])),
            "completed": list(dr.get("completed_actions", [])),
            "failed": list(dr.get("failed_actions", [])),
            "errors": [list(e) for e in dr.get("errors", [])],
            "markdown_path": dr.get("markdown_path"),
            "pdf_path": dr.get("pdf_path"),
            "tracking_path": dr.get("tracking_path"),
        }
        for key in ("markdown_path","pdf_path","tracking_path"):
            pth = dr.get(key)
            if pth:
                fp = Path(pth)
                if not fp.is_absolute():
                    fp = WORKTREE / fp
                print(f"  {key}: exists={fp.is_file()} size={fp.stat().st_size if fp.is_file() else 0}")
                if fp.is_file() and fp.suffix == ".md":
                    txt = fp.read_text(encoding="utf-8")
                    print("   MD has 'Escenario':", "Escenario" in txt)
                    print("   MD has '250':", "250" in txt)
                    report["stages"]["md_preview"] = txt[:800]
                if fp.is_file() and fp.suffix == ".csv":
                    print("   CSV content:\n", fp.read_text(encoding="utf-8"))

print("\n=== 3. EVENTOS (timeline) ===")
ev = read_events(RUN_ID, db_path=settings.events_db_path)
for e in ev:
    print(f"  [{e['id']}] {e['stage']:10s} {e['event_type']:18s} {e['message'][:70]}")

report["stages"]["events_timeline"] = [{"id": e["id"], "stage": e["stage"], "type": e["event_type"], "msg": e["message"]} for e in ev]
report_path = TMP / "e2e_report.json"
report_path.write_text(json.dumps(report, indent=2, default=str, ensure_ascii=False), encoding="utf-8")
print("\nREPORT SAVED:", report_path)
print("TMP DIR:", TMP)
print("TOTAL SECONDS:", round(time.time()-t0,1))
PY