"""Conversión del contrato de Laura; no implementa fórmulas económicas."""
from decimal import Decimal
from src.analysis.calculation_models import CalculationResult, EconomicScenario
from src.analysis.contracts import CalculatedMetric, CalculationContext


def metric_from_break_even(scenario: EconomicScenario, calculation: CalculationResult,
                          *, input_evidence_ids: dict[str, str] | None = None) -> CalculatedMetric:
    """Conserva una copia completa del escenario y del cálculo original.

    Una referencia por entrada observada es necesaria para comprobar su origen.
    Los supuestos no necesitan inventar evidencias. No valida la verdad de fuentes.
    """
    if calculation.calculation_type != "break_even":
        raise ValueError("Este adaptador admite únicamente el punto de equilibrio.")
    result = calculation.result
    return CalculatedMetric(
        metric_id=f"{scenario.scenario_id}.break_even_clients",
        value=Decimal(str(result.value)) if result is not None else None,
        unit=result.unit if result is not None else "clients",
        calculation=calculation.calculation_id,
        evidence_ids=list(calculation.evidence_ids),
        context=CalculationContext(
            scenario=scenario.model_copy(deep=True),
            calculation_result=calculation.model_copy(deep=True),
            input_evidence_ids=dict(input_evidence_ids or {}),
        ),
    )


def metric_context_notes(metric: CalculatedMetric) -> list[str]:
    """Notas que Gema puede conservar en draft.limitations sin recalcular nada."""
    if metric.context is None:
        return []
    context = metric.context
    prefix = f"[{context.scenario.scenario_id}] "
    notes = [
        prefix + f"Supuesto de cálculo: {item.name} = {item.value} {item.unit}."
        for item in context.calculation_result.inputs if item.input_type == "assumption"
    ]
    notes += [prefix + "Supuesto del escenario: " + text for text in context.scenario.assumptions]
    notes += [prefix + "Limitación del cálculo: " + text for text in context.calculation_result.limitations]
    return list(dict.fromkeys(notes))
