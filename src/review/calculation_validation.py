"""Comprueba el contrato de Laura usando su función económica original."""
from decimal import Decimal
from math import isfinite
from src.analysis.economic_calculations import calculate_break_even_clients
from src.review.models import ReviewIssue

INPUT_UNITS = {
    "fixed_costs": "EUR/month",
    "monthly_fee": "EUR/client/month",
    "variable_cost_per_client": "EUR/client/month",
}
OPERATION = "ceil(fixed_costs / (monthly_fee - variable_cost_per_client))"


def check_metric_context(metric, research):
    context = metric.context
    if context is None:
        if metric.calculation.startswith("calc_") or metric.metric_id.startswith("scenario_"):
            raise ValueError("Falta el cálculo original y su escenario.")
        return  # Contrato antiguo: solo comparación; no se declara trazabilidad completa.
    scenario = context.scenario
    calculation = context.calculation_result
    if calculation.calculation_type != "break_even":
        raise ValueError("Tipo de cálculo aún no admitido por la revisión de procedencia.")
    if not calculation.calculation_id.strip() or not scenario.scenario_id.strip():
        raise ValueError("Falta el identificador del cálculo o del escenario.")
    if metric.calculation != calculation.calculation_id:
        raise ValueError("La referencia al cálculo original no coincide.")
    if metric.metric_id != f"{scenario.scenario_id}.break_even_clients":
        raise ValueError("metric_id no corresponde al escenario y al indicador.")
    if metric.evidence_ids != calculation.evidence_ids:
        raise ValueError("La conversión cambió las referencias del cálculo.")
    if len(calculation.evidence_ids) != len(set(calculation.evidence_ids)):
        raise ValueError("El cálculo repite identificadores de evidencias.")
    if calculation.operation != OPERATION:
        raise ValueError("La operación registrada no corresponde al punto de equilibrio.")
    inputs = {item.name: item for item in calculation.inputs}
    if len(inputs) != len(calculation.inputs) or set(inputs) != set(INPUT_UNITS):
        raise ValueError("Las tres entradas del punto de equilibrio deben ser únicas y completas.")
    index = {}
    for evidence in [*research.evidences, *(e for c in research.competitors for e in c.evidences)]:
        if evidence.evidence_id in index and index[evidence.evidence_id] != evidence:
            raise ValueError("Existen evidencias ambiguas con el mismo identificador.")
        index[evidence.evidence_id] = evidence
    for identifier in calculation.evidence_ids:
        if identifier not in index:
            raise ValueError("El cálculo cita una evidencia inexistente.")
    observed = {name for name, item in inputs.items() if item.input_type == "evidence"}
    if set(context.input_evidence_ids) != observed:
        raise ValueError("Cada entrada observada necesita su referencia; los supuestos no se enlazan como observaciones.")
    values = {}
    for name, unit in INPUT_UNITS.items():
        item = inputs[name]
        if item.unit != unit:
            raise ValueError("Unidad incorrecta para " + name)
        if item.value is None or isinstance(item.value, bool) or not isfinite(item.value):
            raise ValueError("Entrada ausente o no finita: " + name)
        if item.input_type not in {"evidence", "assumption"}:
            raise ValueError("Tipo de procedencia inválido.")
        if item.value != getattr(scenario, name):
            raise ValueError("La entrada no corresponde al escenario: " + name)
        if item.input_type == "evidence":
            identifier = context.input_evidence_ids[name]
            if identifier not in calculation.evidence_ids:
                raise ValueError("La referencia de entrada no figura en el cálculo.")
            evidence = index[identifier]
            if not (evidence.source_url or "").strip() or evidence.evidence_id.startswith("access_attempt_") or "[rejected]" in evidence.claim.casefold():
                raise ValueError("Evidencia sin fuente utilizable.")
            if isinstance(evidence.value, bool) or not isinstance(evidence.value, (int, float, Decimal)):
                raise ValueError("La evidencia no contiene un número explícito.")
            if not Decimal(str(evidence.value)).is_finite() or Decimal(str(evidence.value)) != Decimal(str(item.value)):
                raise ValueError("La entrada difiere del valor de su evidencia.")
            # No convertimos EUR/month a EUR/client/month por inferencia.
            if evidence.unit != unit:
                raise ValueError("La unidad de la evidencia no corresponde a la entrada.")
            if evidence.frequency not in (None, "monthly"):
                raise ValueError("La periodicidad de la evidencia no es mensual.")
        values[name] = item.value
    # Se llama a la función de Laura; no se mantiene una segunda fórmula.
    expected = calculate_break_even_clients(**values)
    result = calculation.result
    if result is None:
        if metric.value is not None:
            raise ValueError("La conversión inventó un resultado no disponible.")
        return
    if not isfinite(result.value) or result.value != expected or result.unit != "clients":
        raise ValueError("El resultado original no coincide con la función de Laura.")
    if metric.value != Decimal(str(result.value)) or metric.unit != result.unit:
        raise ValueError("La conversión alteró el valor o la unidad del resultado.")


def validate_calculation_contexts(metrics, research):
    issues = []
    for metric in metrics:
        try:
            check_metric_context(metric, research)
        except (ValueError, TypeError, KeyError, OverflowError) as exc:
            issues.append(ReviewIssue(
                code="invalid_calculation_context", reference_id=metric.metric_id,
                message=str(exc), severity="error", correction_stage="analysis",
            ))
    return issues
