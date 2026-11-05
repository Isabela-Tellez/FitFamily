
from contextlib import ExitStack

import streamlit as st

from src.config import settings
from src.graph.persistence import (
    open_checkpointer,
    load_run as load_persisted_run,
)
from src.graph.workflow import build_workflow
from src.runtime.events import read_recent_events


@st.cache_resource
def get_graph():
    """
    Mantiene una instancia compartida del grafo
    y su conexión SQLite durante la ejecución de Streamlit.
    """
    stack = ExitStack()

    checkpointer = stack.enter_context(
        open_checkpointer(settings.checkpoints_db_path)
    )

    graph = build_workflow(
        checkpointer=checkpointer
    )

    return graph, stack


def get_all_researches():
    """
    Recupera las últimas investigaciones persistidas.

    Deduplica los checkpoints por thread_id y recupera
    el estado más reciente de cada investigación.
    """
    graph, _ = get_graph()

    checkpointer = graph.checkpointer

    if checkpointer is None:
        return []

    thread_ids = set()

    for checkpoint_tuple in checkpointer.list(None):
        configurable = (
            checkpoint_tuple.config.get("configurable", {})
        )

        thread_id = configurable.get("thread_id")

        if thread_id:
            thread_ids.add(thread_id)

    researches = []

    for thread_id in thread_ids:
        snapshot = graph.get_state({
            "configurable": {
                "thread_id": thread_id
            }
        })

        if snapshot and snapshot.values:
            researches.append(snapshot.values)

    researches.sort(
        key=lambda item: item.get("created_at", ""),
        reverse=True,
    )

    return researches


def get_dashboard_metrics():
    """Calcula indicadores a partir de estados persistidos."""

    researches = get_all_researches()

    return {
        "total": len(researches),
        "running": sum(
            r.get("status") == "running"
            for r in researches
        ),
        "completed": sum(
            r.get("status") == "completed"
            for r in researches
        ),
        "awaiting_approval": sum(
            r.get("status") == "awaiting_approval"
            for r in researches
        ),
        "researches": researches,
    }


def get_recent_events(limit=10):
    """Recupera actividad reciente de todas las investigaciones."""

    return read_recent_events(
        limit=limit,
        db_path=settings.events_db_path,
    )


def get_research_by_id(run_id: str):
    """
    Recupera una investigación concreta y verifica su identidad.
    """

    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError(
            "Identificador de investigación inválido."
        )

    graph, _ = get_graph()

    snapshot = load_persisted_run(
        graph=graph,
        thread_id=run_id,
        expected_run_id=run_id,
    )

    if snapshot is None:
        return None

    return snapshot.values
