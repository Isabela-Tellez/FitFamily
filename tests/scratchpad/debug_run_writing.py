import sys
sys.path.insert(0, r'C:\Users\JUAN\Desktop\Proyectos\FitFamily_PR40_PR41_Integration')

from src.agents import strategic_writer
from src.agents.strategic_writer import _make_draft
from src.reporting.models import ReportClaim
from src.schemas import ResearchBrief, ResearchResult, Evidence

# Patch run_writing to add debug output
original_run_writing = strategic_writer.run_writing

def debug_run_writing(brief, research_result):
    print(f"\n=== run_writing called ===")
    result = original_run_writing(brief, research_result)
    print(f"run_writing returned: type={type(result)}, value={result}")
    if result is not None:
        print(f"  result.limitations = {result.limitations}")
    return result

strategic_writer.run_writing = debug_run_writing

def _make_draft(sections: dict[str, str], claims: list[dict]) -> ReportDraft:
    return ReportDraft(
        title="Prueba",
        study_area="Zona de prueba",
        sections=[f"{title}\n{sections.get(title, 'MISSING_SECTION_TEXT')}"
                  for title in [
    "Resumen ejecutivo", "Objetivo y alcance", "Método y fuentes de datos",
    "Público potencial", "Competencia", "Precios y servicios",
    "Análisis visual", "Escenarios económicos", "Oportunidades y riesgos",
    "Incertidumbres", "Próximos pasos"]],
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

print(f"\n=== FINAL RESULT ===")
print(f"draft = {draft}")
if draft is not None:
    print(f"draft.limitations = {draft.limitations}")
else:
    print("draft is None!")