"""Pruebas de persistencia SQLite para las ejecuciones de FitFamily."""

from typing import TypedDict

import pytest
from langgraph.graph import END, START, StateGraph

from src.graph.persistence import (
    build_thread_config,
    open_checkpointer,
    load_run,
)


# Estado mínimo para comprobar el funcionamiento del checkpointer.
class ResearchTestState(TypedDict, total=False):
    topic: str
    result: str


def test_build_thread_config():
    """Comprueba que se genera la configuración correcta de LangGraph."""
    config = build_thread_config("test-001")

    assert config["configurable"]["thread_id"] == "test-001"


def test_build_thread_config_rejects_empty_id():
    """Impide recuperar ejecuciones con un identificador vacío."""
    with pytest.raises(ValueError):
        build_thread_config(" ")


def test_checkpoint_survives_reopening_database(tmp_path):
    """Verifica que el estado se conserva al reabrir la base SQLite."""
    db_path = tmp_path / "checkpoints.sqlite"

    # Construimos un grafo pequeño para probar la persistencia de forma aislada.
    builder = StateGraph(ResearchTestState)
    builder.add_node(
        "save_result",
        lambda state: {"result": "saved"},
    )
    builder.add_edge(START, "save_result")
    builder.add_edge("save_result", END)

    config = build_thread_config("research-001")

    # Ejecutamos el grafo y guardamos su estado en SQLite.
    with open_checkpointer(db_path) as checkpointer:
        graph = builder.compile(checkpointer=checkpointer)
        result = graph.invoke({"topic": "FitFamily"}, config)

        assert result["result"] == "saved"

    # Reabrimos la base para comprobar que el último checkpoint sigue disponible.
    with open_checkpointer(db_path) as checkpointer:
        graph = builder.compile(checkpointer=checkpointer)
        snapshot = graph.get_state(config)

        assert snapshot.values["topic"] == "FitFamily"
        assert snapshot.values["result"] == "saved"
        assert snapshot.next == ()


def test_load_run_returns_existing_checkpoint(tmp_path):
    """Recupera el estado de una ejecución existente."""
    db_path = tmp_path / "checkpoints.sqlite"

    builder = StateGraph(ResearchTestState)
    builder.add_node(
        "save_result",
        lambda state: {"result": "saved"},
    )
    builder.add_edge(START, "save_result")
    builder.add_edge("save_result", END)

    config = build_thread_config("research-load-001")

    with open_checkpointer(db_path) as checkpointer:
        graph = builder.compile(checkpointer=checkpointer)
        graph.invoke({"topic": "FitFamily"}, config)

        snapshot = load_run(graph, "research-load-001")

        assert snapshot is not None
        assert snapshot.values["topic"] == "FitFamily"
        assert snapshot.values["result"] == "saved"


def test_load_run_returns_none_for_unknown_thread(tmp_path):
    """Devuelve None si el hilo no tiene checkpoints."""
    db_path = tmp_path / "checkpoints.sqlite"

    builder = StateGraph(ResearchTestState)
    builder.add_node(
        "save_result",
        lambda state: {"result": "saved"},
    )
    builder.add_edge(START, "save_result")
    builder.add_edge("save_result", END)

    with open_checkpointer(db_path) as checkpointer:
        graph = builder.compile(checkpointer=checkpointer)

        snapshot = load_run(graph, "unknown-research")

        assert snapshot is None
