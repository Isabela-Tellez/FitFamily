"""Comprobaciones de referencias de los informes de FitFamily."""

from collections import Counter

from src.reporting.models import ReportDraft
from src.reporting.report_builder import find_missing_evidence_ids
from src.schemas import ResearchResult


def validate_claim_references(
    draft: ReportDraft,
    research_result: ResearchResult,
) -> list[dict[str, str]]:
    """
    Devuelve los problemas encontrados en las referencias.

    Comprueba:
    - Referencias a evidencias inexistentes.
    - Hechos sin referencias.
    - Identificadores de afirmaciones repetidos.

    No modifica los datos ni verifica el contenido de las fuentes.
    """
    issues: list[dict[str, str]] = []

    # Reutilizamos la comprobación desarrollada por Gema.
    missing_ids = find_missing_evidence_ids(draft, research_result)

    for evidence_id in missing_ids:
        issues.append(
            {
                "code": "missing_evidence",
                "reference_id": evidence_id,
                "message": (
                    f"La evidencia '{evidence_id}' está citada "
                    "pero no aparece en la investigación."
                ),
            }
        )

    # Los hechos deben indicar qué evidencias los respaldan.
    for claim in draft.claims:
        if claim.kind == "fact" and not claim.evidence_ids:
            issues.append(
                {
                    "code": "fact_without_evidence",
                    "reference_id": claim.claim_id,
                    "message": (
                        f"La afirmación '{claim.claim_id}' está marcada "
                        "como hecho, pero no tiene referencias."
                    ),
                }
            )

    # Cada afirmación debe poder identificarse sin ambigüedad.
    claim_counts = Counter(claim.claim_id for claim in draft.claims)

    for claim_id, count in claim_counts.items():
        if count > 1:
            issues.append(
                {
                    "code": "duplicate_claim_id",
                    "reference_id": claim_id,
                    "message": (
                        f"El identificador '{claim_id}' aparece "
                        f"en {count} afirmaciones."
                    ),
                }
            )

    return issues