import sys
sys.path.insert(0, r'C:\Users\JUAN\Desktop\Proyectos\FitFamily_PR40_PR41_Integration')

from src.agents import strategic_writer
from src.reporting.models import ReportClaim, ReportDraft
from src.schemas import ResearchBrief, ResearchResult, Evidence

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

# Llamar directamente a _marcar_contradicciones
_marcar_contradicciones = strategic_writer._marcar_contradicciones
_marcar_contradicciones(d1, [d1, d2])

print("Limitaciones de d1 después de _marcar_contradicciones:")
for l in d1.limitations:
    print(" -", l)

print("\n¿Hay contradicciones detectadas?", any("Contradicciones detectadas" in l for l in d1.limitations))
