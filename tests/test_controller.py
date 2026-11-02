"""Pruebas del controlador principal de FitFamily."""

from dataclasses import asdict
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from src.automation.models import ApprovalRecord, DeliveryResult
from src.runtime import controller


def make_delivery(
    *,
    completed=("export_markdown",),
    failed=(),
):
    return DeliveryResult(
        run_id="run-001",
        draft_id="draft-001",
        draft_version=1,
        draft_fingerprint="fingerprint-001",
        requested_actions=("export_markdown",),
        completed_actions=completed,
        failed_actions=failed,
        markdown_path="outputs/report.md",
    )


class FakeGraph:
    """Simula las operaciones necesarias de LangGraph."""

    def __init__(
        self,
        values=None,
        next_nodes=("approval",),
        invoke_result=None,
    ):
        self.snapshot = SimpleNamespace(
            values=values or {},
            next=next_nodes,
        )
        self.invoke_result = invoke_result or {}
        self.invoke_calls = []
        self.update_calls = []

    def get_state(self, config):
        return self.snapshot

    def invoke(self, command, config):
        self.invoke_calls.append((command, config))
        return self.invoke_result

    def update_state(self, config, values):
        self.update_calls.append((config, values))


def test_start_run_invokes_graph():
    """Inicia una ejecución con el thread_id correcto."""

    graph = FakeGraph(invoke_result={"status": "running"})

    initial_state = {
        "run_id": "run-001",
        "brief": {"topic": "FitFamily"},
    }

    result = controller.start_run(
        graph,
        initial_state,
        "thread-001",
    )

    assert result == {"status": "running"}
    assert len(graph.invoke_calls) == 1

    _, config = graph.invoke_calls[0]

    assert config["configurable"]["thread_id"] == "thread-001"


def test_resume_approval_does_not_execute_delivery_again(
    monkeypatch,
):
    """
    La reanudación recupera el resultado del workflow.

    No debe ejecutar una segunda exportación.
    """

    delivery = make_delivery()

    graph = FakeGraph(
        values={
            "report_version_id": "draft-001:1",
        },
        invoke_result={
            "status": "completed",
            "delivery_result": asdict(delivery),
        },
    )

    result = controller.resume_approval(
        graph=graph,
        thread_id="thread-001",
        decision="approved",
        actions=["export_markdown"],
    )

    assert result == delivery
    assert len(graph.invoke_calls) == 1
    assert graph.update_calls == []


def test_resume_approval_preserves_partial_delivery():
    """Una entrega parcial debe devolverse sin considerarse inválida."""

    delivery = make_delivery(
        completed=("export_markdown",),
        failed=("export_pdf",),
    )

    graph = FakeGraph(
        values={
            "report_version_id": "draft-001:1",
        },
        invoke_result={
            "status": "running",
            "delivery_result": asdict(delivery),
        },
    )

    result = controller.resume_approval(
        graph,
        "thread-001",
        "approved",
        ["export_markdown"],
    )

    assert result == delivery
    assert result.complete is False


def test_resume_approval_returns_none_when_rejected():
    """Una aprobación rechazada no genera una entrega."""

    graph = FakeGraph(
        values={
            "report_version_id": "draft-001:1",
        },
        invoke_result={
            "status": "rejected",
        },
    )

    result = controller.resume_approval(
        graph,
        "thread-001",
        "rejected",
        [],
    )

    assert result is None
    assert len(graph.invoke_calls) == 1


@pytest.mark.parametrize(
    "values,next_nodes,decision,actions,error",
    [
        ({}, ("approval",), "approved",
         ["export_markdown"], "No existe"),
        ({"report_version_id": "draft-001:1"}, (),
         "approved", ["export_markdown"], "no está esperando"),
        ({"report_version_id": "draft-001:1"}, ("review",),
         "approved", ["export_markdown"], "no está esperando"),
        ({"report_version_id": "draft-001:1"}, ("approval",),
         "invalid", ["export_markdown"], "inválida"),
        ({"report_version_id": "draft-001:1"}, ("approval",),
         "approved", [], "al menos una acción"),
        ({"report_version_id": "draft-001:1"}, ("approval",),
         "approved", ["unknown"], "desconocida"),
        ({"report_version_id": "draft-001:1"}, ("approval",),
         "approved", ["export_markdown", "export_markdown"],
         "duplicadas"),
        ({"report_version_id": "draft-001:1"}, ("approval",),
         "rejected", ["export_markdown"], "no puede exportarse"),
        ({"report_version_id": "draft-001:1"}, ("approval",),
         "approved", [[]], "cadenas"),
        ({"report_version_id": None}, ("approval",),
         "approved", ["export_markdown"], "versión válida"),
    ],
)
def test_resume_approval_validations(
    values,
    next_nodes,
    decision,
    actions,
    error,
):
    """Comprueba las validaciones de entrada y del checkpoint."""

    graph = FakeGraph(
        values=values,
        next_nodes=next_nodes,
    )

    with pytest.raises(ValueError, match=error):
        controller.resume_approval(
            graph,
            "thread-001",
            decision,
            actions,
        )

    assert graph.invoke_calls == []


def test_resume_approval_requires_delivery_result():
    """No acepta una aprobación sin resultado de entrega."""

    graph = FakeGraph(
        values={
            "report_version_id": "draft-001:1",
        },
        invoke_result={
            "status": "completed",
        },
    )

    with pytest.raises(
        ValueError,
        match="resultado de entrega",
    ):
        controller.resume_approval(
            graph,
            "thread-001",
            "approved",
            ["export_markdown"],
        )


def test_retry_delivery_delegates_to_workflow():
    """El controlador delega el reintento en el nodo de entrega."""

    graph = FakeGraph(
        values={
            "approval_record": {
                "approved": True,
            },
            "delivery_result": None,
        },
        next_nodes=(),
        invoke_result={
            "delivery_result": asdict(make_delivery()),
        },
    )

    result = controller.retry_delivery(
        graph,
        "thread-001",
        "outputs/reports",
        "outputs/tracking.csv",
    )

    assert result == make_delivery()

    # La actualización y la transición se delegan en un único Command.
    assert graph.update_calls == []
    assert len(graph.invoke_calls) == 1

    command, config = graph.invoke_calls[0]

    assert command.goto == "delivery"

    assert command.update["status"] == "running"
    assert command.update["delivery_output_dir"] == "outputs/reports"
    assert command.update["delivery_csv_path"] == "outputs/tracking.csv"

    assert config["configurable"]["thread_id"] == "thread-001"

    # La ejecución se delega a LangGraph.
    assert len(graph.invoke_calls) == 1

    command, config = graph.invoke_calls[0]

    assert command.goto == "delivery"
    assert config["configurable"]["thread_id"] == "thread-001"


def test_retry_delivery_rejects_missing_approval():
    """Impide reintentar una entrega sin autorización."""

    graph = FakeGraph(
        values={
            "report_draft": {},
        },
        next_nodes=(),
    )

    with pytest.raises(
        ValueError,
        match="autorización",
    ):
        controller.retry_delivery(
            graph,
            "thread-001",
            "outputs/reports",
        )


def test_retry_delivery_rejects_unapproved_record():
    """Impide ejecutar acciones con una autorización rechazada."""

    approval = ApprovalRecord(
        run_id="run-001",
        draft_id="draft-001",
        draft_version=1,
        draft_fingerprint="fingerprint-001",
        approved=False,
        actions=(),
        decided_at=datetime.now(timezone.utc),
    )

    graph = FakeGraph(
        values={
            "approval_record": {
                **asdict(approval),
                "actions": [],
                "decided_at": approval.decided_at.isoformat(),
            },
        },
        next_nodes=(),
    )

    with pytest.raises(
        ValueError,
        match="no está aprobada",
    ):
        controller.retry_delivery(
            graph,
            "thread-001",
            "outputs/reports",
        )
