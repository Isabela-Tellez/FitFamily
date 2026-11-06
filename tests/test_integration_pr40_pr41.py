"""Integración real de PR #40 y PR #41: análisis → redacción → informe →
revisión → aprobación → entrega.

Mocks solo en fronteras externas:
- ``src.graph.nodes.run_research`` (investigación web)
- ``src.agents.strategic_writer.run_writing`` (proveedor LLM)

Son reales: cálculos económicos, adaptador, ``build_report``, validación de
contextos de cálculo, revisión de calidad, lógica de aprobación humana y
exportación local de archivos. Las bases de datos y las exportaciones usan
``tmp_path``. Datos exclusivamente ficticios.
"""

import csv
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from src.analysis.calculation_adapter import metric_context_notes
from src.automation.delivery import ACTION_ORDER
from src.config import settings
from src.graph.nodes import (
    analysis_node,
    approval_node,
    delivery_node,
    research_node,
    review_node,
    writing_node,
)
from src.graph.persistence import build_thread_config, open_checkpointer
from src.graph.state import ResearchState, create_initial_state
from src.graph.workflow import build_workflow
from src.reporting.models import ReportDraft
from src.reporting.templates import (
    MISSING_SECTION_TEXT,
    REPORT_SECTION_TITLES,
)
from src.schemas import Evidence, ResearchBrief, ResearchResult

# ============================================================
# DATOS FICTICIOS
# ============================================================

# 250 clientes: ingresos 10.000 €, variables 2.500 €,
# resultado mensual 1.500 € y punto de equilibrio 200 clientes.
BRIEF = {
    "business_type": "gimnasio con ludoteca",
    "location": "Madrid",
    "study_area": "El Cañaveral",
    "questions": [],
    "assumed_params": {
        "expected_clients": 250,
        "monthly_fee": 40.0,
        "fixed_costs": 6000.0,
        "variable_cost_per_client": 10.0,
    },
}


def make_research() -> ResearchResult:
    """Investigación ficticia válida para la revisión."""
    return ResearchResult(
        evidences=[
            Evidence(
                evidence_id="evidence_ficticia_001",
                claim=(
                    "Gimnasio con ludoteca en la zona ficticia "
                    "(dato inventado para la prueba)."
                ),
                source_url="https://example.invalid/ficticio",
            )
        ],
        coverage_percentage=80.0,
        search_performed="Búsqueda ficticia para la prueba.",
    )


def make_llm_draft(brief: ResearchBrief) -> ReportDraft:
    """Borrador que devolvería el proveedor LLM (frontera externa)."""
    return ReportDraft(
        title="Informe de viabilidad de FitFamily (ficticio)",
        study_area=brief.study_area,
        sections=[
            f"{title}\n{MISSING_SECTION_TEXT}"
            for title in REPORT_SECTION_TITLES
        ],
        sources=[],
        limitations=[],
    )


def _fake_writing(brief, research_result):
    """Sustituto de ``run_writing``: devuelve un borrador nuevo."""
    return make_llm_draft(brief)


def make_state(tmp_path, run_id: str | None = None) -> dict:
    """Estado inicial con las rutas de entrega dentro de ``tmp_path``."""
    state = create_initial_state(
        run_id=run_id or f"integration-{uuid4().hex[:8]}",
        brief=dict(BRIEF),
    )
    state["delivery_output_dir"] = str(tmp_path / "reports")
    state["delivery_csv_path"] = str(tmp_path / "tracking.csv")
    return state


def run_to_approval(tmp_path, run_id: str | None = None) -> dict:
    """Ejecuta investigación → análisis → redacción → revisión reales.

    Solo se sustituyen las fronteras externas (web y LLM).
    """
    state = make_state(tmp_path, run_id=run_id)

    with patch(
        "src.graph.nodes.run_research",
        return_value=make_research(),
    ):
        state.update(research_node(state))

    state.update(analysis_node(state))

    with patch(
        "src.agents.strategic_writer.run_writing",
        side_effect=_fake_writing,
    ):
        state.update(writing_node(state))

    state.update(review_node(state))
    return state


def build_approval_graph(checkpointer):
    """Grafo mínimo con el nodo real de aprobación."""
    builder = StateGraph(ResearchState)
    builder.add_node("approval", approval_node)
    builder.add_edge(START, "approval")
    builder.add_edge("approval", END)
    return builder.compile(checkpointer=checkpointer)


def approve_via_interrupt(state, tmp_path, *, actions=None, resume=None):
    """Pausa en la aprobación y reanuda con la decisión indicada."""
    suffix = uuid4().hex[:8]
    config = build_thread_config(f"approval-{suffix}")

    with open_checkpointer(tmp_path / f"approval-{suffix}.sqlite") as cp:
        graph = build_approval_graph(cp)
        graph.invoke(state, config=config)

        snapshot = graph.get_state(config)
        assert len(snapshot.interrupts) == 1

        version_id = snapshot.interrupts[0].value["report_version_id"]

        payload = resume if resume is not None else {
            "decision": "approved",
            "report_version_id": version_id,
            "draft_fingerprint": snapshot.interrupts[0].value["draft_fingerprint"],
            "actions": actions
            if actions is not None
            else list(ACTION_ORDER),
        }
        if resume is None:
            payload["report_version_id"] = version_id

        return graph.invoke(Command(resume=payload), config=config)


# ============================================================
# A + B + C: ANÁLISIS, REDACCIÓN E INFORME CON CONTEXTO
# ============================================================

def test_analysis_produces_four_contextual_metrics(tmp_path):
    """El análisis genera los cuatro indicadores con su contexto real."""
    state = run_to_approval(tmp_path)

    analysis = state["analysis_result"]
    metrics = {
        metric["metric_id"]: metric
        for metric in analysis["calculated_metrics"]
    }

    assert len(metrics) == 4

    # Los cuatro indicadores conservan escenario y cálculo originales.
    for metric in metrics.values():
        assert metric["context"] is not None
        assert metric["context"]["scenario"]["scenario_id"] == (
            "scenario_intermediate"
        )
        assert metric["calculation"].startswith("calc_")

    # Identificadores prefijados por escenario (Corrección A).
    assert set(metrics) == {
        "scenario_intermediate.monthly_revenue",
        "scenario_intermediate.monthly_variable_costs",
        "scenario_intermediate.monthly_result",
        "scenario_intermediate.break_even_clients",
    }

    # Valores reales calculados con las funciones de Laura.
    assert float(
        metrics["scenario_intermediate.monthly_revenue"]["value"]
    ) == 10000.0
    assert float(
        metrics["scenario_intermediate.monthly_variable_costs"]["value"]
    ) == 2500.0
    assert float(
        metrics["scenario_intermediate.monthly_result"]["value"]
    ) == 1500.0
    assert float(
        metrics["scenario_intermediate.break_even_clients"]["value"]
    ) == 200.0


def test_writing_builds_report_with_traceable_claims(tmp_path):
    """La redacción integra las métricas reales en el informe."""
    state = run_to_approval(tmp_path)

    draft = state["report_draft"]
    claims = draft["claims"]

    # Una afirmación por indicador, sin identificadores repetidos.
    assert len(claims) == 4
    claim_ids = [claim["claim_id"] for claim in claims]
    assert len(claim_ids) == len(set(claim_ids))

    by_metric = {claim["metric_id"]: claim for claim in claims}
    assert set(by_metric) == {
        "scenario_intermediate.monthly_revenue",
        "scenario_intermediate.monthly_variable_costs",
        "scenario_intermediate.monthly_result",
        "scenario_intermediate.break_even_clients",
    }

    # Unidades y valores declarados coinciden con el análisis.
    assert by_metric["scenario_intermediate.monthly_revenue"][
        "reported_unit"
    ] == "EUR/month"
    assert by_metric["scenario_intermediate.break_even_clients"][
        "reported_unit"
    ] == "clients"
    assert by_metric["scenario_intermediate.monthly_result"][
        "reported_value"
    ] == 1500.0

    # Las afirmaciones son inferencias basadas en supuestos.
    for claim in claims:
        assert claim["kind"] == "inference"

    # El informe conserva las notas de trazabilidad del cálculo.
    limitations = draft["limitations"]
    assert any(
        "Punto de equilibrio" in note or "escenario" in note
        for note in limitations
    )

    # El apartado económico está presente y calculado.
    economic = [
        section
        for section in draft["sections"]
        if section.startswith("Escenarios económicos")
    ]
    assert economic
    assert "1500" in economic[0] or "1.500" in economic[0]

    # La versión del informe queda registrada para la aprobación.
    assert state["report_version_id"] == (
        f"{draft['draft_id']}:{draft['version']}"
    )


def test_report_limitations_include_all_calculation_notes(tmp_path):
    """Cada métrica aporta sus notas de contexto al informe."""
    from src.analysis.contracts import CalculatedMetric

    state = run_to_approval(tmp_path)
    draft = state["report_draft"]

    for item in state["analysis_result"]["calculated_metrics"]:
        metric = CalculatedMetric.model_validate(item)
        for note in metric_context_notes(metric):
            assert note in draft["limitations"]


# ============================================================
# D: REVISIÓN Y RECHAZO DE ERRORES BLOQUEANTES
# ============================================================

def test_review_passes_report_without_blocking_errors(tmp_path):
    """La revisión real acepta el informe integrado."""
    state = run_to_approval(tmp_path)

    assert state["status"] == "awaiting_approval"
    assert state["review_route"] == "pending_review"

    review = state["review_result"]
    assert all(
        issue["severity"] != "error" for issue in review["issues"]
    )
    assert "calculation_context" in review["checks_performed"]
    assert "numeric_values" in review["checks_performed"]


def test_review_rejects_report_with_blocking_errors(tmp_path):
    """Un hecho sin evidencia bloquea el informe hasta corregirlo."""
    state = run_to_approval(tmp_path)

    state["report_draft"]["claims"].append(
        {
            "claim_id": "hecho_sin_evidencia",
            "text": "El mercado crece un 10 % anual (ficticio).",
            "kind": "fact",
            "evidence_ids": [],
        }
    )

    result = review_node(state)

    issues = result["review_result"]["issues"]
    assert any(
        issue["code"] == "fact_without_evidence"
        and issue["severity"] == "error"
        for issue in issues
    )

    # Se solicita una corrección de redacción y se cuenta la ronda.
    assert result["review_route"] == "revise_writing"
    assert result["status"] == "running"
    assert result["correction_rounds"] == 1

    # Sin margen de corrección, la revisión bloquea la ejecución.
    exhausted = dict(state)
    exhausted["correction_rounds"] = settings.max_revisions

    blocked = review_node(exhausted)
    assert blocked["review_route"] == "blocked"
    assert blocked["status"] == "stopped_insufficient_evidence"


# ============================================================
# E: APROBACIÓN HUMANA
# ============================================================

def test_approval_interrupts_and_registers_valid_actions(tmp_path):
    """La aprobación pausa, valida la versión y registra acciones."""
    state = run_to_approval(tmp_path)
    suffix = uuid4().hex[:8]
    config = build_thread_config(f"approval-{suffix}")

    with open_checkpointer(tmp_path / f"approval-{suffix}.sqlite") as cp:
        graph = build_approval_graph(cp)
        graph.invoke(state, config=config)

        snapshot = graph.get_state(config)
        assert len(snapshot.interrupts) == 1

        request = snapshot.interrupts[0].value
        assert request["type"] == "human_approval"
        assert request["allowed_decisions"] == ["approved", "rejected"]
        assert request["available_actions"] == list(ACTION_ORDER)

        version_id = request["report_version_id"]
        assert version_id == state["report_version_id"]

        # Se aprueba con las acciones en orden distinto al autorizado:
        # el registro debe normalizarlas al orden establecido.
        result = graph.invoke(
            Command(
                resume={
                    "decision": "approved",
                    "draft_fingerprint": snapshot.interrupts[0].value["draft_fingerprint"],
                    "report_version_id": version_id,
                    "actions": [
                        "update_tracking_csv",
                        "export_pdf",
                        "export_markdown",
                    ],
                }
            ),
            config=config,
        )

    assert result["approval_decision"] == "approved"
    assert result["authorized_actions"] == [
        "export_markdown",
        "export_pdf",
        "update_tracking_csv",
    ]
    assert result["approved_version_id"] == version_id

    # Aprobar no significa que la entrega esté completada.
    assert result["delivery_status"] == "not_started"
    assert result["delivery_result"] is None
    assert result["status"] == "running"
    assert result["current_stage"] == "delivery"


def test_rejection_leaves_no_approval_or_delivery(tmp_path):
    """Rechazar no registra versión aprobada ni acciones."""
    state = run_to_approval(tmp_path, run_id="integration-reject")
    suffix = uuid4().hex[:8]
    config = build_thread_config(f"approval-{suffix}")

    with open_checkpointer(tmp_path / f"approval-{suffix}.sqlite") as cp:
        graph = build_approval_graph(cp)
        graph.invoke(state, config=config)

        snapshot = graph.get_state(config)
        version_id = snapshot.interrupts[0].value["report_version_id"]

        result = graph.invoke(
            Command(
                resume={
                    "decision": "rejected",
                    "report_version_id": version_id,
                }
            ),
            config=config,
        )

    assert result["approval_decision"] == "rejected"
    assert result["approval_record"] is None
    assert result["approved_version_id"] is None
    assert result["authorized_actions"] == []
    assert result["status"] == "rejected"
    assert result["current_stage"] == "rejected"


@pytest.mark.parametrize(
    ("actions", "esperado"),
    [
        ([], "lista válida"),
        (["export_markdown", "export_markdown"], "lista válida"),
        (["exportar_informe"], "lista válida"),
        (["update_tracking_csv"], "Markdown o PDF"),
    ],
)
def test_approval_rejects_invalid_actions(tmp_path, actions, esperado):
    """La aprobación exige acciones válidas, únicas y con formato."""
    state = run_to_approval(tmp_path)

    with pytest.raises(ValueError, match=esperado):
        approve_via_interrupt(state, tmp_path, actions=actions)


def test_approval_rejects_mismatched_version(tmp_path):
    """Una decisión de otra versión del informe se rechaza."""
    state = run_to_approval(tmp_path)

    with pytest.raises(ValueError, match="versión actual"):
        approve_via_interrupt(
            state,
            tmp_path,
            resume={
                "decision": "approved",
                "report_version_id": "otra_version:9",
                "actions": ["export_markdown"],
            },
        )


def test_writing_invalidates_previous_approval(tmp_path):
    """Cambiar el informe anula la aprobación y bloquea la entrega."""
    state = run_to_approval(tmp_path)
    approved = approve_via_interrupt(state, tmp_path)

    assert approved["approval_decision"] == "approved"
    assert approved["approved_version_id"] is not None

    state.update(approved)

    with patch(
        "src.agents.strategic_writer.run_writing",
        side_effect=_fake_writing,
    ):
        rewritten = writing_node(state)

    # La aprobación anterior queda invalidada.
    assert rewritten["approval_decision"] is None
    assert rewritten["approval_record"] is None
    assert rewritten["approved_version_id"] is None
    assert rewritten["authorized_actions"] == []
    assert rewritten["delivery_result"] is None
    assert rewritten["delivery_status"] == "not_started"

    # Y la entrega con la aprobación vieja ya no es posible.
    state.update(rewritten)
    with pytest.raises(ValueError, match="aprobación"):
        delivery_node(state)


# ============================================================
# F: ENTREGA REAL DE ARCHIVOS
# ============================================================

def _approved_state(tmp_path, run_id: str | None = None) -> dict:
    """Estado real aprobado, listo para entregar."""
    state = run_to_approval(tmp_path, run_id=run_id)
    approved = approve_via_interrupt(state, tmp_path)
    state.update(approved)
    return state


def test_delivery_exports_markdown_pdf_and_tracking(tmp_path):
    """La entrega genera Markdown, PDF y seguimiento reales."""
    state = _approved_state(tmp_path, run_id="integration-delivery")

    result = delivery_node(state)

    assert result["delivery_status"] == "completed"
    assert result["status"] == "completed"

    paths = result["export_paths"]
    assert len(paths) == 3

    for path in paths:
        assert Path(path).exists()

    assert any(path.endswith(".md") for path in paths)
    assert any(path.endswith(".pdf") for path in paths)

    csv_path = tmp_path / "tracking.csv"
    assert csv_path.exists()

    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))

    # Cabecera más una fila: una sola entrega registrada.
    assert len(rows) == 2


def test_delivery_is_idempotent_on_retry(tmp_path):
    """Un reintento conserva las rutas y no duplica el seguimiento."""
    state = _approved_state(tmp_path, run_id="integration-idempotent")

    first = delivery_node(state)

    # Simula el reintento del controlador: sigue aprobado y con el
    # resultado anterior conservado, pero la ejecución vuelve a correr.
    retry = {**state, **first, "status": "running"}
    second = delivery_node(retry)

    assert second["delivery_status"] == "completed"
    assert second["export_paths"] == first["export_paths"]

    with (tmp_path / "tracking.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.reader(handle))

    assert len(rows) == 2


def test_delivery_requires_valid_approval(tmp_path):
    """Sin aprobación registrada no se exporta nada."""
    state = run_to_approval(tmp_path, run_id="integration-no-approval")

    with pytest.raises(ValueError, match="aprobación"):
        delivery_node(state)

    assert not (tmp_path / "reports").exists()
    assert not (tmp_path / "tracking.csv").exists()


# ============================================================
# EXTREMO A EXTREMO: GRAFO COMPLETO CON NODOS REALES
# ============================================================

def test_end_to_end_workflow_research_to_delivery(tmp_path):
    """Flujo completo: investigación → análisis → informe → revisión →
    aprobación humana → entrega, con fronteras externas mockeadas."""
    config = build_thread_config("integration-e2e")

    with open_checkpointer(tmp_path / "checkpoints.sqlite") as cp:
        graph = build_workflow(
            checkpointer=cp,
            events_db_path=tmp_path / "events.sqlite",
        )

        state = make_state(tmp_path, run_id="integration-e2e")

        with (
            patch(
                "src.graph.nodes.run_research",
                return_value=make_research(),
            ),
            patch(
                "src.agents.strategic_writer.run_writing",
                side_effect=_fake_writing,
            ),
        ):
            graph.invoke(state, config=config)

        # El flujo se pausa en la aprobación humana.
        snapshot = graph.get_state(config)
        assert len(snapshot.interrupts) == 1

        values = snapshot.values
        assert values["status"] == "awaiting_approval"
        assert values["review_route"] == "pending_review"

        # Las cuatro métricas reales llegaron al informe.
        metrics = values["analysis_result"]["calculated_metrics"]
        assert len(metrics) == 4
        assert all(metric["context"] is not None for metric in metrics)

        draft_claims = values["report_draft"]["claims"]
        assert len(draft_claims) == 4

        version_id = values["report_version_id"]

        # Aprobación humana con las tres acciones autorizadas.
        result = graph.invoke(
            Command(
                resume={
                    "decision": "approved",
                    "draft_fingerprint": snapshot.interrupts[0].value["draft_fingerprint"],
                    "report_version_id": version_id,
                    "actions": [
                        "export_markdown",
                        "export_pdf",
                        "update_tracking_csv",
                    ],
                }
            ),
            config=config,
        )

    # La entrega se ejecuta con archivos reales en tmp_path.
    assert result["approval_decision"] == "approved"
    assert result["delivery_status"] == "completed"
    assert result["status"] == "completed"

    paths = result["export_paths"]
    assert len(paths) == 3
    for path in paths:
        assert Path(path).exists()

    assert (tmp_path / "tracking.csv").exists()
    assert (tmp_path / "reports").is_dir()


@pytest.mark.parametrize("changed", ["draft", "research", "analysis"])
def test_approval_requires_current_review(tmp_path, changed):
    state = run_to_approval(tmp_path)
    if changed == "draft":
        state["report_draft"]["title"] += " (modificado)"
    elif changed == "research":
        state["research_result"]["unresolved_questions"].append("Pregunta posterior")
    else:
        state["analysis_result"]["calculated_metrics"][0]["context"]["scenario"]["assumptions"].append("Nuevo supuesto")
    with pytest.raises(ValueError):
        approve_via_interrupt(state, tmp_path)
    assert not list(tmp_path.rglob("*.pdf"))


@pytest.mark.parametrize("shown_hash", [None, "vista-previa-antigua"])
def test_approval_requires_fingerprint_of_displayed_preview(tmp_path, shown_hash):
    state = run_to_approval(tmp_path)
    decision = {
        "decision": "approved",
        "report_version_id": state["report_version_id"],
        "actions": ["export_markdown"],
    }
    if shown_hash is not None:
        decision["draft_fingerprint"] = shown_hash
    with pytest.raises(ValueError, match="huella"):
        approve_via_interrupt(state, tmp_path, resume=decision)


def test_resume_from_reopened_sqlite_uses_displayed_preview(tmp_path):
    from src.runtime.controller import resume_run
    from src.ui.controller import draft_from_state
    from src.ui.report_preview import render_report_preview

    state = make_state(tmp_path)
    run_id = state["run_id"]
    db = tmp_path / "restart.sqlite"
    config = build_thread_config(run_id)
    with open_checkpointer(db) as cp:
        graph = build_workflow(checkpointer=cp, events_db_path=tmp_path / "events.sqlite")
        with patch("src.graph.nodes.run_research", return_value=make_research()), patch(
            "src.agents.strategic_writer.run_writing", side_effect=_fake_writing
        ):
            graph.invoke(state, config=config)
        paused = graph.get_state(config).values
        preview = render_report_preview(draft_from_state(paused["report_draft"]))
    with open_checkpointer(db) as cp:
        graph = build_workflow(checkpointer=cp, events_db_path=tmp_path / "events.sqlite")
        result = resume_run(graph, run_id, {
            "decision": "approved", "report_version_id": paused["report_version_id"],
            "draft_fingerprint": preview.draft_fingerprint, "actions": ["export_markdown"],
        })
    assert tuple(result.completed_actions) == ("export_markdown",)
    assert Path(result.markdown_path).is_file()
    assert not list(tmp_path.rglob("*.pdf"))
    assert not list(tmp_path.rglob("*.csv"))
