import math
from math import isfinite
from uuid import uuid4
from typing import Literal

from src.analysis.calculation_models import (
    CalculationInput,
    CalculationResult,
    CalculationValue,
    EconomicScenario,
)

def calculate_break_even_clients(
    fixed_costs: float,
    monthly_fee: float,
    variable_cost_per_client: float,
) -> int:
    """
    Calcula el número mínimo de clientes necesarios para cubrir los costes.

    Parámetros:
        fixed_costs: costes fijos mensuales en euros.
        monthly_fee: cuota mensual por cliente en euros.
        variable_cost_per_client: coste variable mensual por cliente en euros.

    Devuelve:
        Número mínimo de clientes necesarios para alcanzar el punto de equilibrio.

    Lanza:
        ValueError: si los valores son negativos o el margen por cliente no es positivo.
    """
    # Comprobamos que todos los importes sean números finitos.
    if not all(
        isfinite(value)
        for value in (
            fixed_costs,
            monthly_fee,
            variable_cost_per_client,
        )
    ):
        raise ValueError("All financial inputs must be finite numbers.")
    
    # Comprobamos que los importes sean válidos.
    if fixed_costs < 0:
        raise ValueError("Fixed costs cannot be negative.")

    if monthly_fee < 0:
        raise ValueError("Monthly fee cannot be negative.")

    if variable_cost_per_client < 0:
        raise ValueError("Variable cost per client cannot be negative.")

    # Calculamos cuánto aporta cada cliente para cubrir los costes fijos.
    contribution_margin = monthly_fee - variable_cost_per_client

    # Si el margen no es positivo, no existe un punto de equilibrio finito.
    if contribution_margin <= 0:
        raise ValueError(
            "Monthly fee must be greater than variable cost per client."
        )

    # Redondeamos hacia arriba porque necesitamos clientes enteros.
    return math.ceil(fixed_costs / contribution_margin)

def create_break_even_calculation(
    fixed_costs: float,
    monthly_fee: float,
    variable_cost_per_client: float,
    evidence_ids: list[str] | None = None,
    limitations: list[str] | None = None,
    input_types: dict[str, Literal["evidence", "assumption"]] | None = None,
) -> CalculationResult:
    """Calcula el punto de equilibrio y registra cómo se ha obtenido."""

    # Calculamos el número mínimo de clientes con la función existente.
    break_even_clients = calculate_break_even_clients(
        fixed_costs=fixed_costs,
        monthly_fee=monthly_fee,
        variable_cost_per_client=variable_cost_per_client,
    )

    # Registramos los valores utilizados y sus unidades.
    inputs = [
        CalculationInput(
            name="fixed_costs",
            value=fixed_costs,
            unit="EUR/month",
            input_type=(input_types or {}).get(
                "fixed_costs",
                "assumption",
            ),
        ),
        CalculationInput(
            name="monthly_fee",
            value=monthly_fee,
            unit="EUR/client/month",
            input_type=(input_types or {}).get(
                "monthly_fee",
                "assumption",
            ),
        ),
        CalculationInput(
            name="variable_cost_per_client",
            value=variable_cost_per_client,
            unit="EUR/client/month",
            input_type=(input_types or {}).get(
                "variable_cost_per_client",
                "assumption",
            ),
        ),
    ]

    # Devolvemos el resultado junto con la fórmula y las referencias.
    return CalculationResult(
        calculation_id=f"calc_break_even_{uuid4().hex}",
        calculation_type="break_even",
        inputs=inputs,
        operation=(
            "ceil(fixed_costs / "
            "(monthly_fee - variable_cost_per_client))"
        ),
        result=CalculationValue(
            value=break_even_clients,
            unit="clients",
        ),
        evidence_ids=evidence_ids or [],
        limitations=limitations or [],
    )

def calculate_monthly_revenue(
    scenario: EconomicScenario,
    evidence_ids: list[str] | None = None,
    limitations: list[str] | None = None,
) -> CalculationResult:
    """
    Calcula los ingresos mensuales previstos y registra su trazabilidad.

    Parámetros:
        scenario: escenario económico con los clientes y la cuota previstos.
        evidence_ids: identificadores de las evidencias utilizadas.
        limitations: limitaciones o advertencias del cálculo.

    Devuelve:
        Un resultado con las entradas, la fórmula y los ingresos calculados.
    """
    # Calculamos los ingresos mensuales previstos.
    monthly_revenue = scenario.expected_clients * scenario.monthly_fee

    # Registramos los valores utilizados, sus unidades y su procedencia.
    inputs = [
        CalculationInput(
            name="expected_clients",
            value=scenario.expected_clients,
            unit="clients",
            input_type="assumption",
        ),
        CalculationInput(
            name="monthly_fee",
            value=scenario.monthly_fee,
            unit="EUR/client/month",
            input_type="assumption",
        ),
    ]

    # Devolvemos el resultado con su propia identificación y trazabilidad.
    return CalculationResult(
        calculation_id=f"calc_monthly_revenue_{uuid4().hex}",
        calculation_type="monthly_revenue",
        inputs=inputs,
        operation="expected_clients * monthly_fee",
        result=CalculationValue(
            value=monthly_revenue,
            unit="EUR/month",
        ),
        evidence_ids=evidence_ids or [],
        limitations=limitations or [],
    )

def calculate_monthly_result(
    monthly_revenue: float,
    monthly_variable_costs: float,
    fixed_costs: float,
    evidence_ids: list[str] | None = None,
    limitations: list[str] | None = None,
) -> CalculationResult:
    """
    Calcula el resultado mensual después de descontar los costes.

    Parámetros:
        monthly_revenue: ingresos mensuales previstos en euros.
        monthly_variable_costs: costes variables mensuales en euros.
        fixed_costs: costes fijos mensuales en euros.
        evidence_ids: identificadores de las evidencias utilizadas.
        limitations: limitaciones o advertencias del cálculo.

    Devuelve:
        Un registro del resultado mensual y su trazabilidad.
    """
    # Calculamos el resultado después de descontar ambos tipos de costes.
    monthly_result = (
        monthly_revenue - monthly_variable_costs - fixed_costs
    )

    # Registramos los valores que intervienen en la operación.
    inputs = [
        CalculationInput(
            name="monthly_revenue",
            value=monthly_revenue,
            unit="EUR/month",
            input_type="assumption",
        ),
        CalculationInput(
            name="monthly_variable_costs",
            value=monthly_variable_costs,
            unit="EUR/month",
            input_type="assumption",
        ),
        CalculationInput(
            name="fixed_costs",
            value=fixed_costs,
            unit="EUR/month",
            input_type="assumption",
        ),
    ]

    # Devolvemos el resultado con su fórmula y trazabilidad.
    return CalculationResult(
        calculation_id=f"calc_monthly_result_{uuid4().hex}",
        calculation_type="monthly_result",
        inputs=inputs,
        operation=(
            "monthly_revenue - monthly_variable_costs - fixed_costs"
        ),
        result=CalculationValue(
            value=monthly_result,
            unit="EUR/month",
        ),
        evidence_ids=evidence_ids or [],
        limitations=limitations or [],
    )

def calculate_monthly_variable_costs(
    scenario: EconomicScenario,
    evidence_ids: list[str] | None = None,
    limitations: list[str] | None = None,
) -> CalculationResult:
    """
    Calcula los costes variables mensuales y registra su trazabilidad.

    Parámetros:
        scenario: escenario económico con los clientes y costes previstos.
        evidence_ids: identificadores de las evidencias utilizadas.
        limitations: limitaciones o advertencias del cálculo.

    Devuelve:
        Un resultado con las entradas, la fórmula y los costes calculados.
    """
    # Calculamos los costes variables para el número de clientes previsto.
    monthly_variable_costs = (
        scenario.expected_clients * scenario.variable_cost_per_client
    )

    # Registramos los valores utilizados y sus unidades.
    inputs = [
        CalculationInput(
            name="expected_clients",
            value=scenario.expected_clients,
            unit="clients",
            input_type="assumption",
        ),
        CalculationInput(
            name="variable_cost_per_client",
            value=scenario.variable_cost_per_client,
            unit="EUR/client/month",
            input_type="assumption",
        ),
    ]

    # Devolvemos el resultado con su propia identificación y trazabilidad.
    return CalculationResult(
        calculation_id=f"calc_monthly_variable_costs_{uuid4().hex}",
        calculation_type="monthly_variable_costs",
        inputs=inputs,
        operation="expected_clients * variable_cost_per_client",
        result=CalculationValue(
            value=monthly_variable_costs,
            unit="EUR/month",
        ),
        evidence_ids=evidence_ids or [],
        limitations=limitations or [],
    )