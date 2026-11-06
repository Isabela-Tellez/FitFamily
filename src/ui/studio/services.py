"""Servicios de datos para la interfaz Studio.

Envuelve la API pública del backend (`src.runtime.controller` y
`src.runtime.events`) sin reimplementar lógica de negocio: toda la
ejecución, recuperación, aprobación y entrega real vive en
`src.graph` y `src.runtime`.

La interfaz nunca invoca nodos del grafo por su cuenta. Tampoco
calcula indicadores económicos: los lee del estado devuelto por el
controlador.
"""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator
from uuid import uuid4

import streamlit as st

from src.config import settings
from src.graph.persistence import open_checkpointer
from src.graph.workflow import build_workflow
from src.mcp.client import call_area_statistics, connect_mcp, list_mcp_tools
from src.runtime import controller
from src.runtime.events import read_events
from src.schemas import ResearchBrief
from src.ui.studio.state import redact_secrets, run_async

# ---------------------------------------------------------------------------
# Rutas: única fuente de verdad (ajustables con variables de entorno)
# ---------------------------------------------------------------------------
EVENTS_DB = settings.events_db_path
CHECKPOINTS_DB = settings.checkpoints_db_path
OUTPUT_DIR = settings.output_dir
TRACKING_CSV = settings.tracking_csv_path


@contextmanager
def graph_session() -> Iterator[Any]:
    """Grafo compilado con persistencia para una operación.

    El checkpointer solo permanece abierto durante la operación:
    no se acumulan conexiones entre reruns de Streamlit.
    """
    CHECKPOINTS_DB.parent.mkdir(parents=True, exist_ok=True)
    with open_checkpointer(CHECKPOINTS_DB) as checkpointer:
        yield build_workflow(
            checkpointer=checkpointer,
            events_db_path=EVENTS_DB,
        )


def _normalize(result: Any) -> dict[str, Any]:
    """Adapta el retorno mixto del controlador (snapshot o estado)."""
    values = getattr(result, "values", None)
    if isinstance(values, dict):
        return values
    if isinstance(result, dict):
        return result
    raise RuntimeError("El controlador no devolvió un estado de ejecución.")


# ---------------------------------------------------------------------------
# Ejecución — creación, recuperación y evolución vía controlador
# ---------------------------------------------------------------------------
def start_study(
    brief: ResearchBrief,
    on_progress: Callable[[str], None] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Crea la ejecución mediante el controlador real (`start_run`).

    `start_run` es idempotente: reenviar el mismo run_id con el mismo
    encargo devuelve la ejecución existente sin duplicarla.

    `on_progress` recibe, desde el hilo principal, el mensaje del
    último evento real registrado por el workflow (registro de eventos
    `src.runtime.events`), para mostrar la evolución del proceso.

    Devuelve (run_id, estado final).
    """
    run_id = uuid4().hex
    brief_dict = brief.model_dump(mode="json")

    holder: dict[str, Any] = {}
    done = threading.Event()

    def _worker() -> None:
        try:
            with graph_session() as graph:
                holder["result"] = controller.start_run(
                    graph, run_id, brief_dict
                )
        except Exception as exc:  # se relanza en el hilo principal
            holder["error"] = exc
        finally:
            done.set()

    worker = threading.Thread(target=_worker, daemon=True)
    worker.start()

    # El hilo principal consulta la evolución real mientras se ejecuta.
    last_id = 0
    while not done.is_set():
        done.wait(timeout=0.4)
        if on_progress is not None:
            try:
                fresh = read_events(
                    run_id, after_id=last_id, db_path=EVENTS_DB
                )
            except Exception:
                fresh = []
            if fresh:
                last_id = fresh[-1]["id"]
                on_progress(fresh[-1]["message"])

    worker.join()
    if "error" in holder:
        raise holder["error"]
    return run_id, _normalize(holder["result"])


def load_study(run_id: str) -> dict[str, Any] | None:
    """Recupera una ejecución persistida mediante `load_run`."""
    with graph_session() as graph:
        snapshot = controller.load_run(graph, run_id)
    if snapshot is None:
        return None
    values = getattr(snapshot, "values", None)
    return dict(values) if values else None


def decide_approval(
    run_id: str,
    report_version_id: str,
    decision: str,
    actions: list[str],
) -> tuple[dict[str, Any], Any]:
    """Registra la decisión humana mediante `resume_run`.

    El controlador valida versión, acciones permitidas y prohibición
    de exportar tras un rechazo; `approval_node` realiza la validación
    definitiva antes de crear el ApprovalRecord.

    Devuelve (estado recargado, DeliveryResult | None).
    """
    with graph_session() as graph:
        outcome = controller.resume_run(
            graph,
            run_id,
            {
                "decision": decision,
                "report_version_id": report_version_id,
                "actions": actions,
            },
        )
        state = _normalize(controller.load_run(graph, run_id) or outcome)
    delivery = outcome if hasattr(outcome, "completed_actions") else None
    return state, delivery


def retry_delivery(run_id: str) -> Any:
    """Reintenta la entrega autorizada mediante `retry_delivery`."""
    with graph_session() as graph:
        return controller.retry_delivery(
            graph,
            run_id,
            output_dir=OUTPUT_DIR,
            csv_path=TRACKING_CSV,
        )


# ---------------------------------------------------------------------------
# Evolución y trabajos anteriores (datos reales de la DB de eventos)
# ---------------------------------------------------------------------------
def run_events(run_id: str, after_id: int = 0) -> list[dict[str, Any]]:
    """Eventos reales registrados para una ejecución."""
    try:
        return read_events(run_id, after_id=after_id, db_path=EVENTS_DB)
    except Exception:
        return []


def list_runs(limit: int = 20) -> list[dict[str, Any]]:
    """Ejecuciones registradas en la DB de eventos (más recientes).

    Solo consulta: no crea ni modifica nada. Devuelve identificador,
    último estado comunicado y marca temporal.
    """
    if not Path(EVENTS_DB).is_file():
        return []
    with sqlite3.connect(str(EVENTS_DB), timeout=10) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT e.run_id, e.stage, e.event_type, e.message, e.timestamp
            FROM research_events e
            JOIN (
                SELECT run_id, MAX(id) AS last_id
                FROM research_events
                GROUP BY run_id
            ) latest ON latest.last_id = e.id
            ORDER BY e.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Estado previo a ejecutar: requisitos reales de los servicios
# ---------------------------------------------------------------------------
def provider_status() -> dict[str, str]:
    """Estado honesto de los servicios externos configurados."""
    import os

    groq = bool(os.getenv("GROQ_API_KEY", "").strip())
    tavily = bool(os.getenv("TAVILY_API_KEY", "").strip())
    return {
        "llm": "Redacción ✓" if groq else "Redacción ✗",
        "search": "Búsqueda ✓" if tavily else "Búsqueda ✗",
        "llm_ready": "yes" if groq else "no",
        "search_ready": "yes" if tavily else "no",
    }


# ---------------------------------------------------------------------------
# MCP — indicadores oficiales (solo bajo petición explícita)
# ---------------------------------------------------------------------------
async def _query_mcp() -> dict:
    async with connect_mcp() as session:
        tools = await list_mcp_tools(session)
        tool_names = [tool.name for tool in tools]
        if "get_area_statistics" not in tool_names:
            raise RuntimeError("El servidor MCP no publica get_area_statistics.")
        return await call_area_statistics(session, "el-cañaveral")


def load_mcp() -> None:
    """Consulta el servidor MCP local y guarda la respuesta en sesión."""
    try:
        with st.spinner("Actualizando los indicadores oficiales…"):
            payload = run_async(_query_mcp())
        if payload.get("error"):
            raise RuntimeError(payload["error"])
        st.session_state["ff_mcp"] = payload
        st.session_state["ff_mcp_error"] = None
    except Exception as exc:
        st.session_state["ff_mcp"] = None
        st.session_state["ff_mcp_error"] = redact_secrets(exc)


# ---------------------------------------------------------------------------
# Recomendación determinista (mismo servicio que la app original)
# ---------------------------------------------------------------------------
def recommend(
    scenario_type: str,
    expected_clients: int,
    monthly_fee: float,
    fixed_costs: float,
    variable_cost_per_client: float,
):
    """Ejecuta el modelo de recomendación real. Devuelve (resultado, error).

    Si el servidor MCP o el registro de competidores no están disponibles,
    el modelo se ejecuta con indicator_source="none" y reporta qué falta,
    en lugar de lanzar una excepción.
    """
    try:
        from src.recommendation.service import recommend as _recommend

        # La fuente verificada depende de si la persona ya consultó los
        # indicadores oficiales en esta sesión. El cálculo no cambia.
        indicator_source = "MCP" if st.session_state.get("ff_mcp") else "none"
        result = _recommend(
            scenario_type=scenario_type,
            expected_clients=expected_clients,
            monthly_fee=monthly_fee,
            fixed_costs=fixed_costs,
            variable_cost_per_client=variable_cost_per_client,
            indicator_source=indicator_source,
            competitor_registry_path="data/processed/competitor_registry.json",
            rent_status="pending",
            run_id="fitfamily-recommendation-studio-001",
        )
        return result, None
    except Exception as exc:
        return None, redact_secrets(exc)
