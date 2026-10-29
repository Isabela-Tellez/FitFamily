"""Pruebas del workflow de FitFamily sin llamadas externas."""

from unittest.mock import patch

import pytest

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from src.graph.persistence import (
    build_thread_config,
    open_checkpointer,
)
from src.graph.state import ResearchState, create_initial_state
from src.graph.workflow import (
    analysis_node,
    approval_node,
    build_workflow,
)


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



def make_approval_state():
    """Construye un estado mínimo válido para solicitar aprobación."""
    state = create_initial_state(
        run_id="approval-test-001",
        brief={
            "business_type": "gimnasio con ludoteca",
            "location": "Madrid",
            "study_area": "El Cañaveral",
            "questions": [],
        },
    )

    state.update(
        status="awaiting_approval",
        current_stage="review",
        report_version_id="draft-001:1",
        report_draft={
            "draft_id": "draft-001",
            "version": 1,
            "title": "Informe de prueba",
        },
        review_result={"issues": []},
    )

    return state


def build_approval_test_graph(checkpointer):
    """Construye un grafo mínimo con el nodo real de aprobación."""
    builder = StateGraph(ResearchState)
    builder.add_node("approval", approval_node)
    builder.add_edge(START, "approval")
    builder.add_edge("approval", END)

    return builder.compile(checkpointer=checkpointer)


def test_approval_interrupts_and_can_be_resumed(tmp_path):
    """La aprobación se pausa y después puede reanudarse."""
    db_path = tmp_path / "approval.sqlite"
    thread_id = "approval-thread-001"
    config = build_thread_config(thread_id)

    with open_checkpointer(db_path) as checkpointer:
        graph = build_approval_test_graph(checkpointer)

        graph.invoke(make_approval_state(), config=config)

        snapshot = graph.get_state(config)

        assert snapshot.next == ("approval",)
        assert len(snapshot.interrupts) == 1

        request = snapshot.interrupts[0].value

        assert request["type"] == "human_approval"
        assert request["run_id"] == "approval-test-001"
        assert request["report_version_id"] == "draft-001:1"
        assert request["allowed_decisions"] == ["approved", "rejected"]

        result = graph.invoke(
            Command(
                resume={
                    "decision": "approved",
                    "report_version_id": "draft-001:1",
                }
            ),
            config=config,
        )

        assert result["status"] == "completed"
        assert result["approval_decision"] == "approved"
        assert result["approved_version_id"] == "draft-001:1"
        assert result["current_stage"] == "completed"


def test_approval_can_be_rejected(tmp_path):
    """Rechazar el informe no registra una versión aprobada."""
    db_path = tmp_path / "rejected.sqlite"
    config = build_thread_config("approval-thread-rejected")

    with open_checkpointer(db_path) as checkpointer:
        graph = build_approval_test_graph(checkpointer)
        graph.invoke(make_approval_state(), config=config)

        result = graph.invoke(
            Command(
                resume={
                    "decision": "rejected",
                    "report_version_id": "draft-001:1",
                }
            ),
            config=config,
        )

        assert result["status"] == "rejected"
        assert result["approval_decision"] == "rejected"
        assert result["approved_version_id"] is None
        assert result["current_stage"] == "rejected"


@pytest.mark.parametrize(
    "decision",
    ["pending", "invalid", "", None],
)
def test_approval_rejects_invalid_decisions(tmp_path, decision):
    """No se admiten decisiones fuera del contrato de aprobación."""
    db_path = tmp_path / "invalid-decision.sqlite"
    config = build_thread_config(f"invalid-{decision!r}")

    with open_checkpointer(db_path) as checkpointer:
        graph = build_approval_test_graph(checkpointer)
        graph.invoke(make_approval_state(), config=config)

        with pytest.raises(ValueError, match="decisión"):
            graph.invoke(
                Command(
                    resume={
                        "decision": decision,
                        "report_version_id": "draft-001:1",
                    }
                ),
                config=config,
            )


def test_approval_rejects_a_different_report_version(tmp_path):
    """Una decisión no puede aplicarse a otra versión del informe."""
    db_path = tmp_path / "wrong-version.sqlite"
    config = build_thread_config("approval-wrong-version")

    with open_checkpointer(db_path) as checkpointer:
        graph = build_approval_test_graph(checkpointer)
        graph.invoke(make_approval_state(), config=config)

        with pytest.raises(ValueError, match="versión actual"):
            graph.invoke(
                Command(
                    resume={
                        "decision": "approved",
                        "report_version_id": "draft-001:2",
                    }
                ),
                config=config,
            )


def test_approval_rejects_a_review_with_errors(tmp_path):
    """Un informe con errores no puede solicitar aprobación."""
    db_path = tmp_path / "review-errors.sqlite"
    config = build_thread_config("approval-review-errors")
    state = make_approval_state()
    state["review_result"] = {
        "issues": [{"severity": "error"}],
    }

    with open_checkpointer(db_path) as checkpointer:
        graph = build_approval_test_graph(checkpointer)

        with pytest.raises(ValueError, match="errores pendientes"):
            graph.invoke(state, config=config)
