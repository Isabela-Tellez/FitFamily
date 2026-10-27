from src.analysis.calculation_models import (
    CalculationInput,
    CalculationValue,
    CalculationResult,
)


def test_calculation_result_stores_inputs_and_result():
    # Creamos las entradas del punto de equilibrio.
    inputs = [
        CalculationInput(
            name="fixed_costs",
            value=6000,
            unit="EUR/month",
            input_type="assumption",
        ),
        CalculationInput(
            name="monthly_fee",
            value=40,
            unit="EUR/client/month",
            input_type="assumption",
        ),
        CalculationInput(
            name="variable_cost_per_client",
            value=10,
            unit="EUR/client/month",
            input_type="assumption",
        ),
    ]

    # Registramos el cálculo con su resultado y sus referencias.
    calculation = CalculationResult(
        calculation_id="calc_break_even_001",
        calculation_type="break_even",
        inputs=inputs,
        operation="fixed_costs / (monthly_fee - variable_cost_per_client)",
        result=CalculationValue(
            value=200,
            unit="clients",
        ),
        evidence_ids=["evidence_example_001"],
        limitations=[],
    )

    # Comprobamos que los datos se han conservado correctamente.
    assert calculation.calculation_id == "calc_break_even_001"
    assert len(calculation.inputs) == 3
    assert calculation.result.value == 200
    assert calculation.result.unit == "clients"
    assert calculation.evidence_ids == ["evidence_example_001"]

def test_calculation_result_allows_missing_result():
    # Un cálculo puede no tener resultado si faltan datos necesarios.
    calculation = CalculationResult(
        calculation_id="calc_incomplete_001",
        calculation_type="break_even",
        operation="fixed_costs / (monthly_fee - variable_cost_per_client)",
        result=None,
        limitations=["Missing variable cost per client."],
    )

    assert calculation.result is None
    assert calculation.limitations == [
        "Missing variable cost per client."
    ]


def test_calculation_result_uses_independent_default_lists():
    # Cada cálculo debe tener sus propias listas de entradas y evidencias.
    first = CalculationResult(
        calculation_id="calc_001",
        calculation_type="break_even",
        operation="example",
    )
    second = CalculationResult(
        calculation_id="calc_002",
        calculation_type="break_even",
        operation="example",
    )

    first.evidence_ids.append("evidence_001")

    assert second.evidence_ids == []
    assert first.inputs == []
    assert second.inputs == []
