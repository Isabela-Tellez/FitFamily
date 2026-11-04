"""Pruebas del workflow de FitFamily sin llamadas externas."""

from unittest.mock import patch

import pytest

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from src.automation.delivery import ACTION_ORDER
from src.automation.models import DeliveryResult
from src.graph.nodes import (
    analysis_node,
    approval_node,
)
from src.graph.persistence import (
    build_thread_config,
    open_checkpointer,
)
from src.graph.state import (
    ResearchState,
    create_initial_state,
)
from src.graph.workflow import build_workflow

# ============================================================
# FIXTURES
# ============================================================

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
    """Estado con parámetros económicos válidos."""
    return create_initial_state(
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


@pytest.fixture
def simulated_pipeline():
    """Simula investigación, redacción y revisión."""
    with (
        patch("src.graph.nodes.run_research") as research,
        patch("src.graph.nodes.build_report") as writing,
        patch("src.graph.nodes.run_basic_review") as review,
    ):
        yield research, writing, review


# ============================================================
# ESTADO INICIAL
# ============================================================

def test_initial_state_contains_delivery_fields(initial_state):
    """Comprueba los campos de aprobación y entrega."""
    assert initial_state["run_id"] == "research-test-001"

    assert initial_state["status"] == "running"
    assert initial_state["current_stage"] == "research"

    assert initial_state["report_version_id"] is None
    assert initial_state["approved_version_id"] is None

    assert initial_state["approval_decision"] is None
    assert initial_state["approval_record"] is None

    assert initial_state["authorized_actions"] == []

    assert initial_state["delivery_result"] is None
    assert initial_state["delivery_status"] == "not_started"

    assert initial_state["export_paths"] == []
    assert initial_state["stop_reason"] is None


def test_initial_state_contains_tracking_fields(initial_state):
    """Comprueba los datos de seguimiento de ejecución."""
    assert initial_state["created_at"]
    assert initial_state["updated_at"]

    assert initial_state["events"] == []
    assert initial_state["errors"] == []

    assert initial_state["usage"]["calls"] == 0
    assert initial_state["usage"]["cost"] == 0.0

    assert initial_state["budget"] == {}
    assert initial_state["pending_tasks"] == []


def test_initial_state_rejects_empty_run_id():
    """No permite identificadores vacíos."""
    with pytest.raises(ValueError, match="run_id"):
        create_initial_state(
            run_id=" ",
            brief={"business_type": "gimnasio"},
        )


def test_initial_state_rejects_empty_brief():
    """No permite encargos vacíos."""
    with pytest.raises(ValueError, match="brief"):
        create_initial_state(
            run_id="test-001",
            brief={},
        )


# ============================================================
# CONSTRUCCIÓN DEL WORKFLOW
# ============================================================

def test_workflow_builds_successfully():
    """El grafo debe construirse sin ejecutar agentes."""
    graph = build_workflow()

    assert graph is not None


def test_workflow_does_not_execute_agents_during_build(
    initial_state,
    simulated_pipeline,
):
    """Construir el grafo no debe ejecutar los agentes."""
    research, writing, review = simulated_pipeline

    graph = build_workflow()

    assert graph is not None

    research.assert_not_called()
    writing.assert_not_called()
    review.assert_not_called()


def test_workflow_can_be_compiled_with_checkpointer():
    """El workflow acepta un checkpointer opcional."""
    graph = build_workflow(checkpointer=None)

    assert graph is not None


# ============================================================
# ANÁLISIS ECONÓMICO
# ============================================================

def test_analysis_node_calculates_economic_metrics(
    analysis_state,
):
    """Calcula los indicadores cuando los parámetros son válidos."""
    result = analysis_node(analysis_state)

    analysis = result["analysis_result"]

    assert len(analysis["scenarios"]) == 1
    assert len(analysis["calculated_metrics"]) == 4

    assert result["current_stage"] == "writing"

    metrics = {
        metric["metric_id"]: metric
        for metric in analysis["calculated_metrics"]
    }

    assert float(
        metrics["scenario_intermediate.monthly_revenue"]["value"]
    ) == 8000.0

    assert float(
        metrics["scenario_intermediate.monthly_variable_costs"]["value"]
    ) == 2000.0

    assert float(
        metrics["scenario_intermediate.monthly_result"]["value"]
    ) == 0.0

    break_even = metrics[
        "scenario_intermediate.break_even_clients"
    ]

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


def test_analysis_node_reports_missing_parameters(
    analysis_state,
):
    """Informa de los parámetros ausentes."""
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

    assert float(metrics["scenario_intermediate.monthly_revenue"]["value"]) == 0.0
    assert float(metrics["scenario_intermediate.monthly_variable_costs"]["value"]) == 0.0
    assert float(metrics["scenario_intermediate.monthly_result"]["value"]) == -6000.0


# ============================================================
# PREPARACIÓN DE APROBACIÓN
# ============================================================


def make_approval_state():
    """Construye un estado válido para solicitar aprobación."""
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
            "title": "Informe de viabilidad de FitFamily",
            "study_area": "El Cañaveral",
            "sections": [
                "Resumen ejecutivo",
                "Análisis de mercado",
                "Análisis económico",
            ],
            "sources": [],
            "limitations": [],
            "draft_id": "draft-001",
            "version": 1,
            "claims": [],
        },
        review_result={
            "issues": [],
        },
    )

    return state


def build_approval_test_graph(checkpointer):
    """Construye un grafo mínimo con el nodo real de aprobación."""
    builder = StateGraph(ResearchState)

    builder.add_node("approval", approval_node)

    builder.add_edge(START, "approval")
    builder.add_edge("approval", END)

    return builder.compile(checkpointer=checkpointer)


def make_delivery_result(
    *,
    requested=None,
    completed=None,
    failed=None,
    markdown_path="",
    pdf_path="",
    tracking_path="",
):
    """Construye un resultado serializable de entrega."""
    requested = tuple(requested or ACTION_ORDER)
    completed = tuple(completed or ())

    if failed is None:
        failed = tuple(
            action
            for action in requested
            if action not in completed
        )
    else:
        failed = tuple(failed)

    return DeliveryResult(
        run_id="research-test-001",
        draft_id="draft-001",
        draft_version=1,
        draft_fingerprint="fingerprint-test",
        requested_actions=requested,
        completed_actions=completed,
        failed_actions=failed,
        markdown_path=markdown_path,
        pdf_path=pdf_path,
        tracking_path=tracking_path,
        errors=tuple(
            (action, "Error simulado")
            for action in failed
        ),
    )

# ============================================================
# APROBACIÓN HUMANA Y PERSISTENCIA
# ============================================================

def test_approval_interrupts_and_can_be_resumed(tmp_path):
    """La aprobación se pausa y puede reanudarse."""
    db_path = tmp_path / "approval.sqlite"

    config = build_thread_config("approval-thread-001")

    with open_checkpointer(db_path) as checkpointer:
        graph = build_approval_test_graph(checkpointer)

        graph.invoke(
            make_approval_state(),
            config=config,
        )

        snapshot = graph.get_state(config)

        assert snapshot.next == ("approval",)
        assert len(snapshot.interrupts) == 1

        request = snapshot.interrupts[0].value

        assert request["type"] == "human_approval"
        assert request["run_id"] == "approval-test-001"

        assert request["report_version_id"] == "draft-001:1"

        assert request["allowed_decisions"] == [
            "approved",
            "rejected",
        ]

        result = graph.invoke(
            Command(
                resume={
                    "decision": "approved",
                    "report_version_id": "draft-001:1",
                    "actions": [
                        "export_markdown",
                        "export_pdf",
                        "update_tracking_csv",
                    ],
                }
            ),
            config=config,
        )

        # Aprobar no significa que la exportación haya terminado.
        assert result["delivery_status"] == "not_started"
        assert result["delivery_result"] is None
        assert result["export_paths"] == []

        # La aprobación debe quedar vinculada a la versión aprobada.
        assert result["approved_version_id"] == "draft-001:1"
        assert result["current_stage"] == "delivery"
        assert result["status"] == "running"
        assert result["delivery_status"] == "not_started"
        assert result["delivery_result"] is None


def test_approval_can_be_rejected(tmp_path):
    """Rechazar el informe no registra una versión aprobada."""
    db_path = tmp_path / "rejected.sqlite"

    config = build_thread_config(
        "approval-thread-rejected"
    )

    with open_checkpointer(db_path) as checkpointer:
        graph = build_approval_test_graph(checkpointer)

        graph.invoke(
            make_approval_state(),
            config=config,
        )

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

        # El rechazo no autoriza ninguna exportación.
        assert result["authorized_actions"] == []
        assert result["delivery_status"] == "not_started"
        assert result["delivery_result"] is None
        assert result["export_paths"] == []


@pytest.mark.parametrize(
    "decision",
    ["pending", "invalid", "", None],
)
def test_approval_rejects_invalid_decisions(
    tmp_path,
    decision,
):
    """No se admiten decisiones fuera del contrato."""
    db_path = tmp_path / "invalid-decision.sqlite"

    config = build_thread_config(
        f"invalid-{decision!r}"
    )

    with open_checkpointer(db_path) as checkpointer:
        graph = build_approval_test_graph(checkpointer)

        graph.invoke(
            make_approval_state(),
            config=config,
        )

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
    """Una decisión no puede aplicarse a otra versión."""
    db_path = tmp_path / "wrong-version.sqlite"

    config = build_thread_config(
        "approval-wrong-version"
    )

    with open_checkpointer(db_path) as checkpointer:
        graph = build_approval_test_graph(checkpointer)

        graph.invoke(
            make_approval_state(),
            config=config,
        )

        with pytest.raises(
            ValueError,
            match="versión actual",
        ):
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

    config = build_thread_config(
        "approval-review-errors"
    )

    state = make_approval_state()

    state["review_result"] = {
        "issues": [
            {"severity": "error"},
        ],
    }

    with open_checkpointer(db_path) as checkpointer:
        graph = build_approval_test_graph(checkpointer)

        with pytest.raises(
            ValueError,
            match="errores pendientes",
        ):
            graph.invoke(
                state,
                config=config,
            )


# ============================================================
# CONTRATO DEL ESTADO DE ENTREGA
# ============================================================

def test_delivery_state_can_be_updated(initial_state):
    """El estado admite resultados de entrega serializados."""
    initial_state.update(
        status="completed",
        current_stage="completed",
        approval_decision="approved",
        approved_version_id="draft-001:1",
        authorized_actions=[
            "export_markdown",
            "export_pdf",
            "update_tracking_csv",
        ],
        delivery_status="completed",
        delivery_result={
            "run_id": initial_state["run_id"],
            "draft_id": "draft-001",
            "draft_version": 1,
            "requested_actions": [
                "export_markdown",
                "export_pdf",
                "update_tracking_csv",
            ],
            "completed_actions": [
                "export_markdown",
                "export_pdf",
                "update_tracking_csv",
            ],
            "failed_actions": [],
        },
        export_paths=[
            "reports/report.md",
            "reports/report.pdf",
            "tracking.csv",
        ],
    )

    assert initial_state["delivery_status"] == "completed"

    assert len(initial_state["export_paths"]) == 3

    assert initial_state["approval_decision"] == "approved"

    assert initial_state["delivery_result"]["failed_actions"] == []


def test_delivery_state_supports_partial_delivery(initial_state):
    """El estado representa una entrega parcialmente completada."""
    initial_state.update(
        delivery_status="partial",
        delivery_result={
            "completed_actions": [
                "export_markdown",
            ],
            "failed_actions": [
                "export_pdf",
            ],
        },
        export_paths=[
            "reports/report.md",
        ],
    )

    assert initial_state["delivery_status"] == "partial"

    assert initial_state["delivery_result"]["completed_actions"] == [
        "export_markdown",
    ]

    assert initial_state["delivery_result"]["failed_actions"] == [
        "export_pdf",
    ]


def test_delivery_state_supports_failed_delivery(initial_state):
    """El estado permite registrar un fallo de entrega."""
    initial_state.update(
        delivery_status="failed",
        delivery_result={
            "completed_actions": [],
            "failed_actions": [
                "export_markdown",
                "export_pdf",
            ],
        },
    )

    assert initial_state["delivery_status"] == "failed"
    assert initial_state["export_paths"] == []

def test_approval_alone_does_not_complete_delivery(tmp_path):
    """La aprobación no debe confundirse con una exportación."""
    db_path = tmp_path / "approval-without-delivery.sqlite"

    config = build_thread_config("approval-without-delivery")

    with open_checkpointer(db_path) as checkpointer:
        graph = build_approval_test_graph(checkpointer)

        graph.invoke(
            make_approval_state(),
            config=config,
        )

        result = graph.invoke(
            Command(
                resume={
                    "decision": "approved",
                    "report_version_id": "draft-001:1",
                    "actions": [
                        "export_markdown",
                        "export_pdf",
                        "update_tracking_csv",
                    ],
                }
            ),
            config=config,
        )

        assert result["approval_decision"] == "approved"
        assert result["approved_version_id"] == "draft-001:1"

        assert result["status"] == "running"
        assert result["current_stage"] == "delivery"

        assert result["delivery_status"] == "not_started"
        assert result["delivery_result"] is None
        assert result["export_paths"] == []

        assert result["authorized_actions"] == [
            "export_markdown",
            "export_pdf",
            "update_tracking_csv",
        ]