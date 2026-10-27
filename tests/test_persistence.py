"""Pruebas de persistencia SQLite para las ejecuciones de FitFamily."""

from typing import TypedDict

import pytest
from langgraph.graph import END, START, StateGraph

from src.graph.state import create_initial_state

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



def test_research_state_survives_reopening_database(tmp_path):
    """Conserva la identidad, los resultados y la etapa tras reabrir SQLite."""
    db_path = tmp_path / "research.sqlite"
    run_id = "research-2026-001"
    thread_id = "thread-abc123"

    initial_state = create_initial_state(
        run_id=run_id,
        brief={"topic": "FitFamily"},
    )

    # Se simula una investigación que ya ha producido resultados.
    initial_state["research_result"] = {
        "summary": "Resultados de investigación guardados"
    }
    initial_state["current_stage"] = "analysis"

    builder = StateGraph(dict)
    builder.add_node("save_result", lambda state: state)
    builder.add_edge(START, "save_result")
    builder.add_edge("save_result", END)

    config = build_thread_config(thread_id)

    with open_checkpointer(db_path) as checkpointer:
        graph = builder.compile(checkpointer=checkpointer)
        graph.invoke(initial_state, config)

    # Se cierra y se reabre SQLite antes de recuperar el checkpoint.
    with open_checkpointer(db_path) as checkpointer:
        graph = builder.compile(checkpointer=checkpointer)
        snapshot = load_run(graph, thread_id)

        assert snapshot is not None
        assert snapshot.values["run_id"] == run_id
        assert snapshot.values["research_result"] == {
            "summary": "Resultados de investigación guardados"
        }
        assert snapshot.values["current_stage"] == "analysis"


def test_run_id_and_thread_id_are_distinct(tmp_path):
    """La investigación y el hilo tienen identificadores independientes."""
    db_path = tmp_path / "identity.sqlite"

    run_id = "research-2026-001"
    thread_id = "thread-abc123"

    initial_state = create_initial_state(
        run_id=run_id,
        brief={"topic": "FitFamily"},
    )

    builder = StateGraph(dict)
    builder.add_node("save_state", lambda state: state)
    builder.add_edge(START, "save_state")
    builder.add_edge("save_state", END)

    config = build_thread_config(thread_id)

    with open_checkpointer(db_path) as checkpointer:
        graph = builder.compile(checkpointer=checkpointer)
        graph.invoke(initial_state, config)

        snapshot = load_run(graph, thread_id)

        assert snapshot is not None
        assert snapshot.values["run_id"] == run_id
        assert config["configurable"]["thread_id"] == thread_id
        assert snapshot.values["run_id"] != thread_id


def test_load_run_rejects_mismatched_run_id(tmp_path):
    """No permite recuperar un checkpoint como si fuera otra investigación."""
    db_path = tmp_path / "identity-mismatch.sqlite"

    initial_state = create_initial_state(
        run_id="research-2026-001",
        brief={"topic": "FitFamily"},
    )

    builder = StateGraph(dict)
    builder.add_node("save_state", lambda state: state)
    builder.add_edge(START, "save_state")
    builder.add_edge("save_state", END)

    config = build_thread_config("thread-abc123")

    with open_checkpointer(db_path) as checkpointer:
        graph = builder.compile(checkpointer=checkpointer)
        graph.invoke(initial_state, config)

        with pytest.raises(ValueError, match="run_id"):
            load_run(
                graph,
                "thread-abc123",
                expected_run_id="research-2026-999",
            )


def test_checkpoints_are_isolated_by_thread_id(tmp_path):
    """Cada hilo recupera su propio estado."""
    db_path = tmp_path / "isolated.sqlite"

    builder = StateGraph(ResearchTestState)
    builder.add_node("save_result", lambda state: state)
    builder.add_edge(START, "save_result")
    builder.add_edge("save_result", END)

    with open_checkpointer(db_path) as checkpointer:
        graph = builder.compile(checkpointer=checkpointer)

        graph.invoke(
            {"topic": "Investigación A", "result": "resultado A"},
            build_thread_config("thread-A"),
        )
        graph.invoke(
            {"topic": "Investigación B", "result": "resultado B"},
            build_thread_config("thread-B"),
        )

        snapshot_a = load_run(graph, "thread-A")
        snapshot_b = load_run(graph, "thread-B")

        assert snapshot_a is not None
        assert snapshot_b is not None
        assert snapshot_a.values["result"] == "resultado A"
        assert snapshot_b.values["result"] == "resultado B"
        assert snapshot_a.values["topic"] != snapshot_b.values["topic"]

def test_open_checkpointer_creates_parent_directory(tmp_path):
    """Crea el directorio de la base de datos si no existe."""
    db_path = tmp_path / "nested" / "storage" / "checkpoints.sqlite"

    assert not db_path.parent.exists()

    with open_checkpointer(db_path) as checkpointer:
        assert checkpointer is not None

    assert db_path.exists()

@pytest.mark.parametrize("expected_run_id", ["", " ", 123])
def test_load_run_rejects_invalid_expected_run_id(
    tmp_path,
    expected_run_id,
):
    """Valida el identificador esperado antes de recuperar el estado."""
    db_path = tmp_path / "expected-id.sqlite"

    builder = StateGraph(ResearchTestState)
    builder.add_node("save_result", lambda state: state)
    builder.add_edge(START, "save_result")
    builder.add_edge("save_result", END)

    config = build_thread_config("thread-validation")

    with open_checkpointer(db_path) as checkpointer:
        graph = builder.compile(checkpointer=checkpointer)
        graph.invoke({"topic": "FitFamily"}, config)

        with pytest.raises(ValueError):
            load_run(
                graph,
                "thread-validation",
                expected_run_id=expected_run_id,
            )


def test_open_checkpointer_closes_context_after_exception(tmp_path):
    """El contexto libera los recursos si ocurre una excepción."""
    db_path = tmp_path / "exception.sqlite"

    with pytest.raises(RuntimeError, match="simulated failure"):
        with open_checkpointer(db_path) as checkpointer:
            assert checkpointer is not None
            raise RuntimeError("simulated failure")

    # Comprobamos que la base puede volver a abrirse tras la excepción.
    with open_checkpointer(db_path) as checkpointer:
        assert checkpointer is not None
