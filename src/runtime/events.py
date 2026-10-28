
"""Registro persistente de eventos de ejecución de FitFamily."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# Ruta predeterminada de la base de datos de eventos.
DEFAULT_EVENTS_DB_PATH = Path("data") / "fitfamily_events.sqlite"


def _initialize_db(db_path: str | Path) -> None:
    """Crea la tabla y el índice necesarios para registrar eventos."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path, timeout=10) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS research_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                stage TEXT NOT NULL,
                event_type TEXT NOT NULL,
                message TEXT NOT NULL,
                details TEXT NOT NULL
            )
            """
        )

        # Acelera las consultas de eventos por investigación.
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_research_events_run_id_id
            ON research_events (run_id, id)
            """
        )


def emit_event(
    run_id: str,
    stage: str,
    event_type: str,
    message: str,
    details: dict[str, Any] | None = None,
    db_path: str | Path = DEFAULT_EVENTS_DB_PATH,
) -> dict[str, Any]:
    """
    Registra un evento y devuelve sus datos.

    Los eventos se asocian a un run_id para mantener separadas
    las investigaciones y permitir consultar su progreso.
    """
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("run_id no puede estar vacío.")
    if not isinstance(stage, str) or not stage.strip():
        raise ValueError("stage no puede estar vacío.")
    if not isinstance(event_type, str) or not event_type.strip():
        raise ValueError("event_type no puede estar vacío.")
    if not isinstance(message, str) or not message.strip():
        raise ValueError("message no puede estar vacío.")
    if details is not None and not isinstance(details, dict):
        raise ValueError("details debe ser un diccionario.")

    timestamp = datetime.now(timezone.utc).isoformat()
    serialized_details = json.dumps(
        details or {},
        ensure_ascii=False,
        default=str,
    )

    _initialize_db(db_path)
    path = Path(db_path)

    with sqlite3.connect(path, timeout=10) as connection:
        cursor = connection.execute(
            """
            INSERT INTO research_events
                (run_id, timestamp, stage, event_type, message, details)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                timestamp,
                stage,
                event_type,
                message,
                serialized_details,
            ),
        )
        event_id = cursor.lastrowid

    return {
        "id": event_id,
        "run_id": run_id,
        "timestamp": timestamp,
        "stage": stage,
        "event_type": event_type,
        "message": message,
        "details": details or {},
    }


def read_events(
    run_id: str,
    after_id: int = 0,
    limit: int = 100,
    db_path: str | Path = DEFAULT_EVENTS_DB_PATH,
) -> list[dict[str, Any]]:
    """
    Recupera los eventos de una investigación en orden de registro.

    after_id permite consultar solo los eventos nuevos, evitando
    repetir los que ya se han mostrado en la interfaz.
    """
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("run_id no puede estar vacío.")
    if isinstance(after_id, bool) or not isinstance(after_id, int) or after_id < 0:
        raise ValueError("after_id debe ser un entero no negativo.")
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("limit debe ser un entero positivo.")

    _initialize_db(db_path)
    path = Path(db_path)

    with sqlite3.connect(path, timeout=10) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT id, run_id, timestamp, stage, event_type, message, details
            FROM research_events
            WHERE run_id = ? AND id > ?
            ORDER BY id ASC
            LIMIT ?
            """,
            (run_id, after_id, limit),
        ).fetchall()

    return [
        {
            "id": row["id"],
            "run_id": row["run_id"],
            "timestamp": row["timestamp"],
            "stage": row["stage"],
            "event_type": row["event_type"],
            "message": row["message"],
            "details": json.loads(row["details"]),
        }
        for row in rows
    ]
