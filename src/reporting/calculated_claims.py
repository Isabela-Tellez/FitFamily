"""Genera afirmaciones numéricas desde resultados del análisis."""

from decimal import Decimal
from math import isfinite

from src.analysis.calculation_adapter import SCENARIO_METRICS
from src.analysis.contracts import CalculatedMetric
from src.reporting.models import ReportClaim


SCENARIO_NAMES = {
    "conservative": "conservador",
    "intermediate": "intermedio",
    "optimistic": "optimista",
}


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
        f"En el escenario {SCENARIO_NAMES[context.scenario.scenario_type]}, con las entradas y supuestos "
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
        calculation_id=metric.calculation,
    )

MONTHLY_LABELS = {
    "monthly_revenue": "Ingresos mensuales estimados",
    "monthly_variable_costs": "Costes variables mensuales estimados",
    "monthly_result": "Resultado mensual estimado",
}


def build_scenario_claim(
    metric: CalculatedMetric, *, claim_id: str
) -> ReportClaim | None:
    """Presenta la cifra del escenario sin volver a calcularla."""
    if metric.context is None:
        raise ValueError("La métrica necesita el contexto del cálculo.")
    scenario_id = metric.context.scenario.scenario_id
    calculation_type = metric.context.calculation_result.calculation_type
    if calculation_type == "break_even":
        return build_break_even_claim(metric, claim_id=claim_id)
    if calculation_type not in MONTHLY_LABELS:
        raise ValueError("Tipo de cálculo económico no admitido.")
    suffix, unit = SCENARIO_METRICS[calculation_type]
    if metric.metric_id != f"{scenario_id}.{suffix}" or metric.unit != unit:
        raise ValueError("Identificador o unidad de la métrica incorrectos.")
    if metric.value is None:
        return None

    reported_value = float(metric.value)
    if not isfinite(reported_value) or Decimal(str(reported_value)) != metric.value:
        raise ValueError("El valor no puede convertirse sin alterarlo.")
    amount = format(metric.value, "f").replace(".", ",")
    label = MONTHLY_LABELS[calculation_type]
    scenario_name = SCENARIO_NAMES[metric.context.scenario.scenario_type]
    return ReportClaim(
        claim_id=claim_id,
        text=f"Escenario {scenario_name} — {label}: {amount} €/mes.",
        kind="inference",
        evidence_ids=list(metric.evidence_ids),
        metric_id=metric.metric_id,
        reported_value=reported_value,
        reported_unit=metric.unit,
        calculation_id=metric.calculation,
    )


def format_scenario_note(note: str) -> str | None:
    """Traduce el prefijo visible sin alterar la nota del borrador."""
    for scenario_type, name in SCENARIO_NAMES.items():
        prefix = f"[scenario_{scenario_type}] "
        if note.startswith(prefix):
            detail = note[len(prefix):]
            if detail.startswith(("Supuesto de cálculo: ", "Supuesto del escenario: ")):
                return None
            return f"Escenario {name} · {detail}"
    return note


def format_claim_title(claim: ReportClaim) -> str:
    """Muestra un título legible para las métricas económicas."""
    scenario_id, _, suffix = (claim.metric_id or "").rpartition(".")
    name = SCENARIO_NAMES.get(scenario_id.removeprefix("scenario_"))
    label = (
        "Punto de equilibrio" if suffix == "break_even_clients"
        else MONTHLY_LABELS.get(suffix)
    )
    if name and label:
        return f"{label} · Escenario {name}"
    return claim.claim_id


ECONOMIC_TRACE_HEADERS = ("Escenario", "Métrica", "Valor", "Referencias")


def economic_trace_row(claim: ReportClaim) -> tuple[str, str, str, str] | None:
    """Resume una afirmación económica con las referencias del borrador."""
    label, separator, scenario = format_claim_title(claim).partition(" · Escenario ")
    if not separator or claim.reported_value is None:
        return None
    unit = {"clients": "clientes", "EUR/month": "€/mes"}.get(
        claim.reported_unit, claim.reported_unit
    )
    value = str(claim.reported_value).removesuffix(".0").replace(".", ",")
    evidence = ", ".join(dict.fromkeys(claim.evidence_ids))
    references = f"Métrica: {claim.metric_id}"
    if claim.calculation_id:
        references += f"\nCálculo: {claim.calculation_id}"
    references += f"\nEvidencias: {evidence or 'sin referencias registradas'}"
    return scenario.capitalize(), label, f"{value} {unit}", references
