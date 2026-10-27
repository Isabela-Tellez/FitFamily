
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
        raise ValueError("thread_id debe ser una cadena no vacía.")

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




def load_run(
    graph: Any,
    thread_id: str,
    expected_run_id: str | None = None,
) -> Any | None:
    """
    Recupera el último checkpoint de un hilo existente.

    Devuelve None si no hay estado guardado.
    Si se proporciona expected_run_id, verifica la identidad
    de negocio antes de devolver el checkpoint.
    """
    # Validamos los argumentos antes de consultar el grafo.
    if expected_run_id is not None:
        if (
            not isinstance(expected_run_id, str)
            or not expected_run_id.strip()
        ):
            raise ValueError(
                "expected_run_id debe ser una cadena no vacía."
            )

    config = build_thread_config(thread_id)
    snapshot = graph.get_state(config)

    if not snapshot.values:
        return None

    if expected_run_id is not None:
        actual_run_id = snapshot.values.get("run_id")

        if actual_run_id != expected_run_id:
            raise ValueError(
                "El run_id del checkpoint no coincide "
                "con la investigación esperada."
            )

    return snapshot
