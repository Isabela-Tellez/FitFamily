import os, sys
sys.path.insert(0, r"C:\Users\JUAN\Desktop\Proyectos\FitFamily_PR40_PR41_Integration")
os.environ["FITFAMILY_DATA_DIR"] = r"C:\Users\JUAN\AppData\Local\Temp\fitfamily_e2e_lh9k9zd2\data"
os.environ["FITFAMILY_OUTPUT_DIR"] = r"C:\Users\JUAN\AppData\Local\Temp\fitfamily_e2e_lh9k9zd2\outputs\reports"
os.environ["FITFAMILY_CHECKPOINTS_DB"] = r"C:\Users\JUAN\AppData\Local\Temp\fitfamily_e2e_lh9k9zd2\data\checkpoints.sqlite"
os.environ["FITFAMILY_EVENTS_DB"] = r"C:\Users\JUAN\AppData\Local\Temp\fitfamily_e2e_lh9k9zd2\data\fitfamily_events.sqlite"
os.environ["FITFAMILY_TRACKING_CSV"] = r"C:\Users\JUAN\AppData\Local\Temp\fitfamily_e2e_lh9k9zd2\outputs\tracking.csv"
from src.config import settings
from src.graph.persistence import open_checkpointer
from src.graph.workflow import build_workflow
from src.runtime import controller
from src.runtime.events import read_events
RUN_ID = "fitfamily-e2e-demo-001"
with open_checkpointer(settings.checkpoints_db_path) as ck:
    graph = build_workflow(checkpointer=ck, events_db_path=settings.events_db_path)
    snap = controller.load_run(graph, RUN_ID)
    print("snap exists:", snap is not None)
    if snap:
        st = snap.values if hasattr(snap, "values") else snap
        print("STATUS:", st.get("status"))
        r = st.get("research_result") or {}
        print("EVIDENCES:", len(r.get("evidences", [])))
        for ev in r.get("evidences", []):
            print("  -", ev.get("evidence_id"), "|", ev.get("source_url"))
        print("COMPETITORS:", len(r.get("competitors", [])))
        for c in r.get("competitors", []):
            print("  -", c.get("name"), "|", c.get("location"), "| services:", c.get("services"))
        print("SEARCH_PERFORMED:", r.get("search_performed"))
        print("NOTES:", r.get("notes"))
        print("UNRESOLVED:", r.get("unresolved_questions"))
        a = st.get("analysis_result") or {}
        print("METRICS:", a.get("calculated_metrics"))
        print("ANALYSIS limitations:", a.get("limitations"))
        print("DRAFT exists:", st.get("report_draft") is not None)
        print("REVIEW:", st.get("review_result"))
ev = read_events(RUN_ID, db_path=settings.events_db_path)
print("--- EVENTS ---")
for e in ev:
    print("  [" + str(e["id"]) + "]", e["stage"], e["event_type"], e["message"][:80])
PY