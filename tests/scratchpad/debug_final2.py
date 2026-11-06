import sys
sys.path.insert(0, r'C:\Users\JUAN\Desktop\Proyectos\FitFamily_PR40_PR41_Integration')

import src.agents.strategic_writer as strategic_writer
from src.agents.strategic_writer import _make_draft
from src.reporting.models import ReportClaim
from src.schemas import ResearchBrief, ResearchResult, Evidence

original_run_writing = strategic_writer.run_writing

def debug_run_writing(brief, research_result):
    print(f"\n=== run_writing called ===")
    result = original_run_writing(brief, research_result)
    print(f"run_writing returned: {result}")
    if result is not None:
        print(f"  result.limitations = {result.limitations}")
    else:
        print("  result is None!")
    return result

strategic_writer.run_writing = debug_run_writing

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
    [{"text": "Winfit no publicar tarifas.", "kind": "fact",
      "evidence_ids": ["ev3"]}],
)

research = ResearchResult(
    evidences=[
        Evidence(evidence_id="ev1", claim="Winfit sede", source_url="u1"),
        Evidence(evidence_id="ev2", claim="Winfit precio", source_url="u2"),
        Evidence(evidence_id="ev3", claim="Winfit no publica", source_url="u3"),
    ],
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

strategic_writer._run_writing_single = fake_single
strategic_writer.partition_writer_research = lambda research, fits: [research, research]

draft = strategic_writer.run_writing(brief, research)

print(f"\nFINAL: draft={draft}")
if draft is not None:
    print(f"FINAL: draft.limitations = {draft.limitations}")
