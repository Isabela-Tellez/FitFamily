"""Cálculos reproducibles sobre evidencias explícitas, sin consultas externas."""
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

import pandas as pd

from src.analysis.contracts import CalculatedMetric
from src.analysis.market_analysis import summarize_competitors
from src.analysis.scenarios import calculate_break_even_clients
from src.schemas import ResearchResult

AVERAGE = "src.analysis.market_analysis.summarize_competitors"
IDENTITY = "evidence_value"
BREAK_EVEN = "src.analysis.scenarios.calculate_break_even_clients"


def evidence_index(research: ResearchResult):
    """Deduplica copias idénticas; un mismo id con datos distintos es ambiguo."""
    index = {}
    for evidence in [*research.evidences, *(
        e for competitor in research.competitors for e in competitor.evidences
    )]:
        if not evidence.evidence_id.strip():
            raise ValueError("Evidencia sin identificador.")
        previous = index.get(evidence.evidence_id)
        if previous is not None and previous != evidence:
            raise ValueError("Evidencia ambigua: " + evidence.evidence_id)
        index[evidence.evidence_id] = evidence
    return index


def numeric_value(evidence):
    if evidence.evidence_id.startswith("access_attempt_") or "[rejected]" in evidence.claim.casefold():
        raise ValueError("La evidencia está descartada.")
    url = urlparse(evidence.source_url or "")
    if url.scheme not in {"http", "https"} or not url.netloc:
        raise ValueError("La evidencia requiere una URL de procedencia.")
    if isinstance(evidence.value, bool) or not isinstance(evidence.value, (int, float, Decimal)):
        raise ValueError("La evidencia debe contener un valor numérico explícito.")
    try:
        value = Decimal(str(evidence.value))
    except InvalidOperation as exc:
        raise ValueError("Valor numérico inválido.") from exc
    if not value.is_finite() or value < 0:
        raise ValueError("Se requieren valores finitos no negativos.")
    return value


def evidence_unit(evidence):
    if evidence.unit == "EUR":
        units = {"monthly": "EUR/month", "annual": "EUR/year", "one-time": "EUR"}
        if evidence.frequency not in units:
            raise ValueError("Importe EUR sin periodicidad conocida.")
        return units[evidence.frequency]
    if not evidence.unit or not evidence.unit.strip():
        raise ValueError("Evidencia sin unidad.")
    if evidence.unit not in {"EUR/month", "EUR/year", "clients", "count", "%", "m2"}:
        raise ValueError("Unidad no admitida para cálculo reproducible.")
    return evidence.unit


def recompute(metric: CalculatedMetric, research: ResearchResult):
    """Solo ejecuta operaciones de una lista cerrada; nunca evalúa texto."""
    metric = CalculatedMetric.model_validate(metric.model_dump())
    ids = metric.evidence_ids
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("El cálculo necesita evidencias únicas y no vacías.")
    index = evidence_index(research)
    if any(identifier not in index for identifier in ids):
        raise ValueError("El cálculo cita una evidencia inexistente.")
    sources = [index[identifier] for identifier in ids]
    values = [numeric_value(e) for e in sources]
    units = [evidence_unit(e) for e in sources]
    if metric.calculation == IDENTITY:
        if len(ids) != 1 or metric.input_evidence_ids:
            raise ValueError("Un valor observado necesita exactamente una evidencia.")
        return values[0], units[0]
    if metric.calculation == AVERAGE:
        if metric.input_evidence_ids or any(unit != "EUR/month" for unit in units):
            raise ValueError("La media necesita precios mensuales en EUR.")
        # Se usa la función real de análisis; no una fórmula paralela.
        summary = summarize_competitors(pd.DataFrame({
            "gym_name": ids,
            "monthly_price_eur": [float(v) for v in values],
            "has_playroom": [None] * len(ids),
        }))
        return Decimal(str(summary["average_monthly_price_eur"])), "EUR/month"
    if metric.calculation == BREAK_EVEN:
        roles = {"fixed_costs", "monthly_fee", "variable_cost_per_client"}
        mapping = metric.input_evidence_ids
        if set(mapping) != roles or set(mapping.values()) != set(ids) or len(ids) != 3:
            raise ValueError("El punto de equilibrio requiere tres entradas identificadas por su función.")
        if any(unit != "EUR/month" for unit in units):
            raise ValueError("Las entradas financieras deben ser mensuales en EUR.")
        result = calculate_break_even_clients(**{
            role: float(numeric_value(index[identifier]))
            for role, identifier in mapping.items()
        })
        return Decimal(result), "clients"
    raise ValueError("Operación de cálculo no admitida: " + metric.calculation)


def make_metric(research, *, metric_id, calculation, evidence_ids, input_evidence_ids=None):
    metric = CalculatedMetric(
        metric_id=metric_id, value=None, unit="pending",
        calculation=calculation, evidence_ids=list(evidence_ids),
        input_evidence_ids=dict(input_evidence_ids or {}),
    )
    value, unit = recompute(metric, research)
    return metric.model_copy(update={"value": value, "unit": unit})


def calculate_price_average(research, evidence_ids):
    """Media de la muestra explícita de precios, no del mercado completo."""
    return make_metric(
        research, metric_id="market.average_monthly_price_eur",
        calculation=AVERAGE, evidence_ids=evidence_ids,
    )


def calculate_break_even_metric(research, input_evidence_ids):
    return make_metric(
        research, metric_id="scenario.break_even_clients",
        calculation=BREAK_EVEN, evidence_ids=list(input_evidence_ids.values()),
        input_evidence_ids=input_evidence_ids,
    )


def calculate_observed_metrics(research):
    """Conserva valores observados; no extrae importes del texto libre."""
    metrics = []
    for identifier, evidence in evidence_index(research).items():
        if evidence.value is None:
            continue
        # Los datos no numéricos de investigación no son indicadores.
        if not isinstance(evidence.value, (int, float, Decimal)) or isinstance(evidence.value, bool):
            continue
        metrics.append(make_metric(
            research, metric_id="evidence." + identifier,
            calculation=IDENTITY, evidence_ids=[identifier],
        ))
    return metrics


def validate_metric_provenance(metrics, research):
    from src.review.models import ReviewIssue
    issues = []
    for metric in metrics:
        try:
            value, unit = recompute(metric, research)
            if value != metric.value or unit != metric.unit:
                raise ValueError("El resultado o su unidad no coincide con el cálculo reproducido.")
        except (ValueError, TypeError, OverflowError) as exc:
            issues.append(ReviewIssue(
                code="invalid_metric_provenance", reference_id=metric.metric_id,
                message=str(exc), severity="error", correction_stage="analysis",
            ))
    return issues
