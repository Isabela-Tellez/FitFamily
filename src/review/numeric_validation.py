"""Compara las cifras declaradas con los resultados del análisis."""

from src.analysis.contracts import CalculatedMetric, ReportedMetric
from src.review.models import ReviewIssue
from src.reporting.models import ReportDraft

def validate_reported_metrics(
    reported_metrics: list[ReportedMetric],
    calculated_metrics: list[CalculatedMetric],
) -> list[ReviewIssue]:
    """
    Comprueba que cada cifra declarada coincide con su cálculo.

    No vuelve a calcular los indicadores, no interpreta texto libre
    y no comprueba que los datos originales sean verdaderos.
    """
    issues: list[ReviewIssue] = []

    # Agrupamos por identificador para detectar también duplicados.
    metrics_by_id: dict[str, list[CalculatedMetric]] = {}

    for metric in calculated_metrics:
        metrics_by_id.setdefault(metric.metric_id, []).append(metric)

    for reported in reported_metrics:
        matches = metrics_by_id.get(reported.metric_id, [])

        def add_issue(
            code: str,
            message: str,
            stage: str = "writing",
        ) -> None:
            issues.append(
                ReviewIssue(
                    code=code,
                    reference_id=reported.claim_id,
                    message=message,
                    severity="error",
                    correction_stage=stage,
                )
            )

        if not matches:
            add_issue(
                "missing_calculated_metric",
                f"La afirmación '{reported.claim_id}' cita el indicador "
                f"'{reported.metric_id}', que no está en el análisis.",
            )
            continue

        if len(matches) > 1:
            add_issue(
                "ambiguous_calculated_metric",
                f"El análisis contiene varios resultados con el "
                f"identificador '{reported.metric_id}'.",
                stage="analysis",
            )
            continue

        calculated = matches[0]

        if calculated.value is None:
            add_issue(
                "unavailable_calculated_metric",
                f"La afirmación '{reported.claim_id}' presenta una cifra, "
                "pero el análisis no dispone de un valor calculado.",
            )
            continue

        if reported.reported_unit != calculated.unit:
            add_issue(
                "metric_unit_mismatch",
                f"La afirmación '{reported.claim_id}' usa la unidad "
                f"'{reported.reported_unit}', pero el análisis utiliza "
                f"'{calculated.unit}'.",
            )

        if reported.reported_value != calculated.value:
            add_issue(
                "metric_value_mismatch",
                f"La afirmación '{reported.claim_id}' presenta "
                f"{reported.reported_value}, pero el análisis calcula "
                f"{calculated.value}.",
            )

    return issues

def validate_numeric_claim_links(
    draft: ReportDraft,
) -> list[ReviewIssue]:
    """Comprueba que cada cifra pertenece a una afirmación del borrador."""
    issues: list[ReviewIssue] = []
    claim_ids = {claim.claim_id for claim in draft.claims}
    seen_links: set[tuple[str, str]] = set()

    for reported in draft.reported_metrics:
        if reported.claim_id not in claim_ids:
            issues.append(
                ReviewIssue(
                    code="numeric_claim_not_found",
                    reference_id=reported.claim_id,
                    message=(
                        "La cifra estructurada está asociada a una "
                        "afirmación que no existe en el borrador."
                    ),
                    severity="error",
                    correction_stage="writing",
                )
            )

        # Una afirmación puede contener varios indicadores,
        # pero no debe repetir el mismo vínculo.
        link = (reported.claim_id, reported.metric_id)

        if link in seen_links:
            issues.append(
                ReviewIssue(
                    code="duplicate_numeric_claim_link",
                    reference_id=reported.claim_id,
                    message=(
                        "La afirmación repite una referencia al "
                        f"indicador '{reported.metric_id}'."
                    ),
                    severity="error",
                    correction_stage="writing",
                )
            )

        seen_links.add(link)

    return issues