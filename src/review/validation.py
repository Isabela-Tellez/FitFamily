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

def validate_evidence_quality(
    draft: ReportDraft,
    research_result: ResearchResult,
) -> list[dict[str, str]]:
    """
    Detecta referencias vacías y evidencias inadecuadas para hechos.

    No consulta Internet ni comprueba si el contenido de una fuente
    demuestra realmente la afirmación.
    """
    issues: list[dict[str, str]] = []

    # Evitamos repetir el mismo problema para una misma referencia.
    seen_issues: set[tuple[str, str]] = set()

    def add_issue(code: str, reference_id: str, message: str) -> None:
        key = (code, reference_id)

        if key not in seen_issues:
            issues.append(
                {
                    "code": code,
                    "reference_id": reference_id,
                    "message": message,
                }
            )
            seen_issues.add(key)

    # Recogemos las referencias utilizadas para respaldar hechos.
    fact_evidence_ids: set[str] = set()

    for claim in draft.claims:
        for evidence_id in claim.evidence_ids:
            if not evidence_id.strip():
                add_issue(
                    "empty_evidence_reference",
                    claim.claim_id,
                    f"La afirmación '{claim.claim_id}' contiene "
                    "una referencia vacía.",
                )
            elif claim.kind == "fact":
                fact_evidence_ids.add(evidence_id)

    # Una evidencia puede estar en la lista general o en un competidor.
    evidences = list(research_result.evidences)

    for competitor in research_result.competitors:
        evidences.extend(competitor.evidences)

    for evidence in evidences:
        evidence_id = evidence.evidence_id

        # En este bloque revisamos evidencias citadas por hechos.
        if evidence_id not in fact_evidence_ids:
            continue

        if not (evidence.source_url or "").strip():
            add_issue(
                "evidence_without_source",
                evidence_id,
                f"La evidencia '{evidence_id}' respalda un hecho, "
                "pero no indica su procedencia.",
            )

        if evidence_id.startswith("access_attempt_"):
            add_issue(
                "failed_access_as_evidence",
                evidence_id,
                f"La evidencia '{evidence_id}' registra un acceso "
                "fallido y no puede respaldar un hecho del mercado.",
            )

        # Adaptación al formato actual de la búsqueda de fuentes.
        is_rejected_source = (
            evidence_id.startswith("source_")
            and "[rejected]" in evidence.claim.casefold()
        )

        if is_rejected_source:
            add_issue(
                "rejected_source_as_evidence",
                evidence_id,
                f"La evidencia '{evidence_id}' corresponde a una "
                "fuente descartada y se está usando como respaldo.",
            )

    return issues

def validate_claim_structure(
    draft: ReportDraft,
) -> list[dict[str, str]]:
    """
    Comprueba la estructura de las afirmaciones del informe.

    No determina si una afirmación es verdadera ni si está
    correctamente clasificada desde el punto de vista semántico.
    """
    issues: list[dict[str, str]] = []
    allowed_kinds = ("fact", "assumption", "inference")

    for position, claim in enumerate(draft.claims, start=1):
        # Si falta el identificador, indicamos la posición
        # para que la persona pueda localizar la afirmación.
        valid_id = (
            isinstance(claim.claim_id, str)
            and bool(claim.claim_id.strip())
        )
        reference_id = (
            claim.claim_id
            if valid_id
            else f"claim_position_{position}"
        )

        if not valid_id:
            issues.append({
                "code": "empty_claim_id",
                "reference_id": reference_id,
                "message": (
                    f"La afirmación en la posición {position} "
                    "necesita un identificador no vacío."
                ),
            })

        if not isinstance(claim.text, str) or not claim.text.strip():
            issues.append({
                "code": "empty_claim_text",
                "reference_id": reference_id,
                "message": (
                    f"La afirmación '{reference_id}' "
                    "no tiene un texto válido."
                ),
            })

        if claim.kind not in allowed_kinds:
            issues.append({
                "code": "invalid_claim_kind",
                "reference_id": reference_id,
                "message": (
                    f"La afirmación '{reference_id}' debe clasificarse "
                    "como fact, assumption o inference."
                ),
            })

    return issues