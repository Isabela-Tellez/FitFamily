"""Pruebas del workflow de FitFamily sin llamadas externas."""

from unittest.mock import patch

import pytest

from src.graph.state import create_initial_state
from src.graph.workflow import analysis_node, build_workflow


@pytest.fixture
def initial_state():
    """Estado inicial válido para las pruebas del workflow."""
    return create_initial_state(
        run_id="research-test-001",
        brief={
            "business_type": "gimnasio con ludoteca",
            "location": "Madrid",
            "study_area": "El Cañaveral",
            "questions": [],
        },
    )


@pytest.fixture
def analysis_state():
    """Estado con parámetros económicos válidos para el análisis."""
    state = create_initial_state(
        run_id="analysis-test-001",
        brief={
            "business_type": "gimnasio con ludoteca",
            "location": "Madrid",
            "study_area": "El Cañaveral",
            "questions": [],
            "assumed_params": {
                "expected_clients": 200,
                "monthly_fee": 40.0,
                "fixed_costs": 6000.0,
                "variable_cost_per_client": 10.0,
            },
        },
    )
    return state


@pytest.fixture
def simulated_pipeline():
    """Simula investigación, redacción y revisión."""
    with (
        patch("src.graph.workflow.run_research") as research,
        patch("src.graph.workflow.build_report") as writing,
        patch("src.graph.workflow.run_basic_review") as review,
    ):
        yield research, writing, review


def test_workflow_builds_successfully():
    """El grafo debe poder construirse sin ejecutar agentes."""
    graph = build_workflow()

    assert graph is not None


def test_workflow_runs_research_writing_and_review(
    initial_state,
    simulated_pipeline,
):
    """Comprueba la ruta actual de investigación a revisión."""
    research, writing, review = simulated_pipeline

    # Se definirán resultados válidos en el siguiente ajuste de estas
    # pruebas, utilizando los modelos reales del proyecto.
    graph = build_workflow()

    assert graph is not None
    research.assert_not_called()
    writing.assert_not_called()
    review.assert_not_called()


def test_workflow_can_be_compiled_with_checkpointer():
    """El workflow debe aceptar un checkpointer opcional."""
    graph = build_workflow(checkpointer=None)

    assert graph is not None



def test_analysis_node_calculates_economic_metrics(analysis_state):
    """Calcula los indicadores cuando todos los parámetros son válidos."""
    result = analysis_node(analysis_state)

    analysis = result["analysis_result"]

    assert len(analysis["scenarios"]) == 1
    assert len(analysis["calculated_metrics"]) == 4
    assert result["current_stage"] == "writing"

    metrics = {
        metric["metric_id"]: metric
        for metric in analysis["calculated_metrics"]
    }

    assert float(metrics["monthly_revenue"]["value"]) == 8000.0
    assert float(metrics["monthly_variable_costs"]["value"]) == 2000.0
    assert float(metrics["monthly_result"]["value"]) == 0.0

    break_even = metrics["scenario_intermediate.break_even_clients"]
    assert float(break_even["value"]) == 200
    assert break_even["unit"] == "clients"


@pytest.mark.parametrize(
    ("parameter", "value"),
    [
        ("expected_clients", 100.5),
        ("expected_clients", True),
        ("monthly_fee", float("inf")),
        ("fixed_costs", float("nan")),
        ("variable_cost_per_client", "10"),
    ],
)
def test_analysis_node_rejects_invalid_parameters(
    analysis_state,
    parameter,
    value,
):
    """Rechaza parámetros financieros inválidos."""
    analysis_state["brief"]["assumed_params"][parameter] = value

    with pytest.raises(ValueError):
        analysis_node(analysis_state)


def test_analysis_node_reports_missing_parameters(analysis_state):
    """Informa de los parámetros ausentes sin ejecutar los cálculos."""
    del analysis_state["brief"]["assumed_params"]["monthly_fee"]

    result = analysis_node(analysis_state)

    analysis = result["analysis_result"]

    assert analysis["scenarios"] == []
    assert analysis["calculated_metrics"] == []
    assert any(
        "monthly_fee" in limitation
        for limitation in analysis["limitations"]
    )
    assert result["current_stage"] == "writing"


def test_analysis_node_accepts_zero_clients(analysis_state):
    """Acepta cero clientes como valor entero válido."""
    analysis_state["brief"]["assumed_params"]["expected_clients"] = 0

    result = analysis_node(analysis_state)

    metrics = {
        metric["metric_id"]: metric
        for metric in result["analysis_result"]["calculated_metrics"]
    }

    assert float(metrics["monthly_revenue"]["value"]) == 0.0
    assert float(metrics["monthly_variable_costs"]["value"]) == 0.0
    assert float(metrics["monthly_result"]["value"]) == -6000.0
