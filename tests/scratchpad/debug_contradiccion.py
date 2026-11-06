import sys
sys.path.insert(0, r'C:\Users\JUAN\Desktop\Proyectos\FitFamily_PR40_PR41_Integration')

from src.agents.strategic_writer import _detectar_contradicciones
from src.reporting.models import ReportClaim, ReportDraft
from src.schemas import ResearchBrief, ResearchResult, Evidence

d1 = ReportDraft(
    title="Prueba",
    study_area="Zona",
    sections=["Resumen ejecutivo\nTexto"],
    claims=[
        ReportClaim(
            claim_id="claim_001",
            text="Winfit tiene sede en El Cañaveral.",
            kind="fact",
            evidence_ids=["ev1"],
        )
    ],
    sources=[],
    limitations=[],
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
d2 = ReportDraft(
    title="Prueba",
    study_area="Zona",
    sections=["Resumen ejecutivo\nTexto"],
    claims=[
        ReportClaim(
            claim_id="claim_003",
            text="Winfit no publicar tarifas.",
            kind="fact",
            evidence_ids=["ev3"],
        )
    ],
    sources=[],
    limitations=[],
)

from src.agents.strategic_writer import _detectar_contradicciones
conts = _detectar_contradicciones([d1, d2])
print("Contradicciones:", conts)
