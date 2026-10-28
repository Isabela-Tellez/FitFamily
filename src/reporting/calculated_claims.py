"""Genera afirmaciones numéricas desde resultados del análisis."""

from decimal import Decimal
from math import isfinite

from src.analysis.contracts import CalculatedMetric
from src.reporting.models import ReportClaim


def build_break_even_claim(
    metric: CalculatedMetric,
    *,
    claim_id: str,
) -> ReportClaim | None:
    """Construye una afirmación del punto de equilibrio.

    No recalcula el resultado ni sustituye la revisión de María.
    Si el resultado no está disponible, no genera una cifra.
    """
    # Necesitamos el contexto conservado por el adaptador de María.
    if metric.context is None:
        raise ValueError("La métrica necesita el contexto del cálculo.")

    context = metric.context
    scenario_id = context.scenario.scenario_id

    # Esta primera función solo admite el punto de equilibrio.
    if context.calculation_result.calculation_type != "break_even":
        raise ValueError("Solo se admite el punto de equilibrio.")

    expected_id = f"{scenario_id}.break_even_clients"
    if metric.metric_id != expected_id:
        raise ValueError("La métrica no corresponde al escenario.")

    if metric.unit != "clients":
        raise ValueError("El punto de equilibrio debe expresarse en clientes.")

    # No sustituimos un resultado ausente por cero.
    if metric.value is None:
        return None

    value = metric.value

    # El resultado representa un número entero de clientes.
    if (
        not value.is_finite()
        or value < 0
        or value != value.to_integral_value()
    ):
        raise ValueError(
            "El número de clientes debe ser entero, finito y no negativo."
        )

    # ReportClaim admite int/float. Comprobamos que la conversión
    # no cambie el valor que comparará el revisor.
    reported_value = float(value)
    if (
        not isfinite(reported_value)
        or Decimal(str(reported_value)) != value
    ):
        raise ValueError("El valor no puede convertirse sin alterarlo.")

    # El texto utiliza exactamente el mismo valor registrado.
    clients = int(value)
    client_label = "cliente" if clients == 1 else "clientes"
    text = (
        f"En el escenario {scenario_id}, con las entradas y supuestos "
        f"indicados, se necesitan al menos {clients} {client_label} "
        "para cubrir los costes incluidos en el cálculo mensual. "
        "Esto no garantiza conseguir esa clientela ni la viabilidad "
        "del negocio."
    )

    return ReportClaim(
        claim_id=claim_id,
        text=text,
        kind="inference",
        evidence_ids=list(metric.evidence_ids),
        metric_id=metric.metric_id,
        reported_value=reported_value,
        reported_unit=metric.unit,
    )