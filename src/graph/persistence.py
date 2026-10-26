
"""Persistencia SQLite para las ejecuciones de FitFamily."""

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from langgraph.checkpoint.sqlite import SqliteSaver


# Ruta predeterminada de la base de datos de checkpoints.
DEFAULT_DB_PATH = Path("data") / "fitfamily_checkpoints.sqlite"


def build_thread_config(thread_id: str) -> dict[str, Any]:
    """Construye la configuración de LangGraph para un hilo."""
    if not isinstance(thread_id, str) or not thread_id.strip():
        raise ValueError("thread_id no puede estar vacío.")

    return {
        "configurable": {
            "thread_id": thread_id,
        }
    }


@contextmanager
def open_checkpointer(
    db_path: str | Path = DEFAULT_DB_PATH,
) -> Iterator[SqliteSaver]:
    """
    Abre el checkpointer SQLite y libera los recursos al terminar.

    La conexión debe permanecer abierta mientras se utiliza el grafo.
    """
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with SqliteSaver.from_conn_string(str(path)) as checkpointer:
        yield checkpointer


@contextmanager
def create_checkpointer(
    db_path: str | Path = DEFAULT_DB_PATH,
) -> Iterator[SqliteSaver]:
    """Proporciona un contexto de persistencia para el workflow."""
    with open_checkpointer(db_path) as checkpointer:
        yield checkpointer


def load_run(graph: Any, thread_id: str) -> Any | None:
    """
    Recupera el último checkpoint de un hilo existente.

    Devuelve None si no hay estado guardado.
    El grafo debe estar compilado con su checkpointer.
    """
    config = build_thread_config(thread_id)
    snapshot = graph.get_state(config)

    if not snapshot.values:
        return None

    return snapshot
