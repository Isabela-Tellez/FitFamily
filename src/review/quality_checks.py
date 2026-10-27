"""Ejecución de las comprobaciones básicas del revisor."""
import hashlib
import json
from src.automation.exporter import calculate_draft_fingerprint
from src.reporting.models import ReportDraft
from src.review.models import ReviewIssue, ReviewResult
from src.review.validation import (
    validate_claim_references,
    validate_claim_structure,
    validate_evidence_quality,
)
from src.schemas import ResearchResult
from src.analysis.contracts import CalculatedMetric
from src.review.numeric_validation import (
    validate_numeric_claim_links,
    validate_reported_metrics,
)

def calculate_research_fingerprint(
    research_result: ResearchResult,
) -> str:
    """
    Calcula una huella del contenido de la investigación.

    Incluye evidencias generales, competidores, sus evidencias
    y el resto de los campos de ResearchResult.
    """
    serialized = json.dumps(
        research_result.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )

    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

def calculate_analysis_fingerprint(
    calculated_metrics: list[CalculatedMetric] | None,
) -> str:
    """
    Calcula una huella de los resultados del análisis.

    None significa que no se ha proporcionado el análisis.
    Una lista vacía significa que se ha proporcionado sin indicadores.
    """
    payload = (
        None
        if calculated_metrics is None
        else [
            metric.model_dump(mode="json")
            for metric in calculated_metrics
        ]
    )

    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )

    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

def run_basic_review(
    draft: ReportDraft,
    research_result: ResearchResult,
    *,
    calculated_metrics: list[CalculatedMetric] | None = None,
) -> ReviewResult:
    """
    Revisa referencias, evidencias, estructura y cifras declaradas.

    No modifica los datos ni concede aprobación humana.
    """
    raw_issues = validate_claim_references(draft, research_result)
    raw_issues += validate_evidence_quality(draft, research_result)
    raw_issues += validate_claim_structure(draft)

    issues: list[ReviewIssue] = []

    for item in raw_issues:
        if item["code"] == "evidence_without_source":
            correction_stage = "research"
        else:
            correction_stage = "writing"

        issues.append(
            ReviewIssue(
                code=item["code"],
                reference_id=item["reference_id"],
                message=item["message"],
                severity="error",
                correction_stage=correction_stage,
            )
        )

    checks_performed = [
        "claim_references",
        "evidence_quality",
        "claim_structure",
    ]

    # Activamos la revisión numérica si hay cifras declaradas
    # o si el controlador nos proporciona resultados de análisis.
    if draft.reported_metrics or calculated_metrics is not None:
        checks_performed.append("numeric_claim_links")
        issues.extend(validate_numeric_claim_links(draft))

        if calculated_metrics is None:
            # Hay cifras en el informe, pero no recibimos el análisis.
            # No podemos considerarlas comprobadas.
            checks_performed.append("numeric_analysis_availability")
            issues.append(
                ReviewIssue(
                    code="missing_analysis_context",
                    reference_id=draft.draft_id,
                    message=(
                        "El borrador contiene cifras estructuradas, "
                        "pero falta el análisis necesario para compararlas."
                    ),
                    severity="error",
                    correction_stage="analysis",
                )
            )
        else:
            checks_performed.append("numeric_values")
            issues.extend(
                validate_reported_metrics(
                    draft.reported_metrics,
                    calculated_metrics,
                )
            )

    return ReviewResult(
        draft_id=draft.draft_id,
        draft_version=draft.version,
        draft_fingerprint=calculate_draft_fingerprint(draft),
        issues=tuple(issues),
        checks_performed=tuple(checks_performed),
        research_fingerprint=calculate_research_fingerprint(
            research_result
        ),
        analysis_fingerprint=calculate_analysis_fingerprint(
            calculated_metrics
        ),
    )

def validate_review_matches_draft(
    review: ReviewResult,
    draft: ReportDraft,
) -> None:
    """
    Comprueba que la revisión corresponde al borrador actual.

    Si cambia el identificador, la versión o el contenido,
    es necesario realizar una nueva revisión.
    """
    if review.draft_id != draft.draft_id:
        raise ValueError("La revisión pertenece a otro borrador.")

    if review.draft_version != draft.version:
        raise ValueError("La revisión corresponde a otra versión.")

    current_fingerprint = calculate_draft_fingerprint(draft)

    if review.draft_fingerprint != current_fingerprint:
        raise ValueError(
            "El contenido cambió después de la revisión."
        )
    
def validate_review_matches_research(
    review: ReviewResult,
    research_result: ResearchResult,
) -> None:
    """
    Rechaza una revisión si no corresponde a la investigación actual.

    No modifica los datos ni realiza una nueva revisión.
    """
    if not review.research_fingerprint:
        raise ValueError(
            "La revisión no tiene huella de investigación. "
            "Es necesario revisar de nuevo."
        )

    current_fingerprint = calculate_research_fingerprint(
        research_result
    )

    if review.research_fingerprint != current_fingerprint:
        raise ValueError(
            "La investigación cambió después de la revisión."
        )

def validate_review_matches_analysis(
    review: ReviewResult,
    calculated_metrics: list[CalculatedMetric] | None,
) -> None:
    """Rechaza una revisión si el análisis ha cambiado."""
    if not review.analysis_fingerprint:
        raise ValueError(
            "La revisión no tiene huella de análisis. "
            "Es necesario revisar de nuevo."
        )

    current_fingerprint = calculate_analysis_fingerprint(
        calculated_metrics
    )

    if review.analysis_fingerprint != current_fingerprint:
        raise ValueError(
            "El análisis cambió después de la revisión."
        )