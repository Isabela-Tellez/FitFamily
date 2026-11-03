
"""Registro persistente de eventos de ejecución de FitFamily."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_EVENTS_DB_PATH = Path("data") / "fitfamily_events.sqlite"


def _validate_text(value: str, name: str) -> None:
    """Valida que un campo de texto sea una cadena no vacía."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} debe ser una cadena no vacía.")


def _validate_details(
    details: dict[str, Any] | None,
) -> dict[str, Any]:
    """Valida y normaliza los detalles de un evento."""
    if details is None:
        return {}

    if not isinstance(details, dict):
        raise ValueError("details debe ser un diccionario.")

    return details


def _initialize_db(db_path: str | Path) -> None:
    """Crea la tabla y los índices necesarios."""
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

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_research_events_run_id_id
            ON research_events (run_id, id)
            """
        )

        # Índice para localizar eventos idempotentes.
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_research_events_idempotency
            ON research_events (
                run_id,
                stage,
                event_type,
                details
            )
            """
        )


def _serialize_details(
    details: dict[str, Any],
    *,
    sort_keys: bool = False,
) -> str:
    """Serializa detalles de forma compatible con SQLite."""
    try:
        return json.dumps(
            details,
            ensure_ascii=False,
            sort_keys=sort_keys,
            default=str,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "No se pudieron serializar los detalles del evento."
        ) from exc


def _build_event(
    event_id: int,
    run_id: str,
    timestamp: str,
    stage: str,
    event_type: str,
    message: str,
    details: dict[str, Any],
) -> dict[str, Any]:
    """Construye la representación pública de un evento."""
    return {
        "id": event_id,
        "run_id": run_id,
        "timestamp": timestamp,
        "stage": stage,
        "event_type": event_type,
        "message": message,
        "details": details,
    }


def emit_event(
    run_id: str,
    stage: str,
    event_type: str,
    message: str,
    details: dict[str, Any] | None = None,
    db_path: str | Path = DEFAULT_EVENTS_DB_PATH,
) -> dict[str, Any]:
    """
    Registra un evento de ejecución.

    Cada evento genera un nuevo registro, incluso si existen
    otros eventos con los mismos datos.
    """
    _validate_text(run_id, "run_id")
    _validate_text(stage, "stage")
    _validate_text(event_type, "event_type")
    _validate_text(message, "message")

    normalized_details = _validate_details(details)

    serialized_details = _serialize_details(normalized_details)

    _initialize_db(db_path)

    path = Path(db_path)
    timestamp = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(path, timeout=10) as connection:
        cursor = connection.execute(
            """
            INSERT INTO research_events (
                run_id,
                timestamp,
                stage,
                event_type,
                message,
                details
            )
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

    return _build_event(
        event_id=event_id,
        run_id=run_id,
        timestamp=timestamp,
        stage=stage,
        event_type=event_type,
        message=message,
        details=normalized_details,
    )


def emit_event_once(
    run_id: str,
    stage: str,
    event_type: str,
    message: str,
    details: dict[str, Any] | None = None,
    db_path: str | Path = DEFAULT_EVENTS_DB_PATH,
) -> dict[str, Any]:
    """
    Registra un evento evitando duplicados consecutivos equivalentes.

    La comprobación y la inserción se realizan dentro de una
    transacción BEGIN IMMEDIATE para evitar condiciones de carrera.

    La identidad del evento se determina mediante:
    run_id, stage, event_type y details.
    """
    _validate_text(run_id, "run_id")
    _validate_text(stage, "stage")
    _validate_text(event_type, "event_type")
    _validate_text(message, "message")

    normalized_details = _validate_details(details)

    serialized_details = _serialize_details(
        normalized_details,
        sort_keys=True,
    )

    _initialize_db(db_path)

    path = Path(db_path)
    timestamp = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(path, timeout=10) as connection:
        connection.execute("BEGIN IMMEDIATE")

        row = connection.execute(
            """
            SELECT id, timestamp
            FROM research_events
            WHERE run_id = ?
              AND stage = ?
              AND event_type = ?
              AND details = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (
                run_id,
                stage,
                event_type,
                serialized_details,
            ),
        ).fetchone()

        if row is not None:
            return _build_event(
                event_id=row[0],
                run_id=run_id,
                timestamp=row[1],
                stage=stage,
                event_type=event_type,
                message=message,
                details=normalized_details,
            )

        cursor = connection.execute(
            """
            INSERT INTO research_events (
                run_id,
                timestamp,
                stage,
                event_type,
                message,
                details
            )
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

        return _build_event(
            event_id=cursor.lastrowid,
            run_id=run_id,
            timestamp=timestamp,
            stage=stage,
            event_type=event_type,
            message=message,
            details=normalized_details,
        )


def read_events(
    run_id: str,
    after_id: int = 0,
    limit: int = 100,
    db_path: str | Path = DEFAULT_EVENTS_DB_PATH,
) -> list[dict[str, Any]]:
    """
    Recupera los eventos de una investigación.

    Los eventos se devuelven en orden cronológico de registro.

    after_id permite consultar exclusivamente eventos nuevos,
    facilitando la actualización incremental de la interfaz.
    """
    _validate_text(run_id, "run_id")

    if (
        isinstance(after_id, bool)
        or not isinstance(after_id, int)
        or after_id < 0
    ):
        raise ValueError(
            "after_id debe ser un entero no negativo."
        )

    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or limit < 1
    ):
        raise ValueError(
            "limit debe ser un entero positivo."
        )

    _initialize_db(db_path)

    path = Path(db_path)

    with sqlite3.connect(path, timeout=10) as connection:
        connection.row_factory = sqlite3.Row

        rows = connection.execute(
            """
            SELECT
                id,
                run_id,
                timestamp,
                stage,
                event_type,
                message,
                details
            FROM research_events
            WHERE run_id = ?
              AND id > ?
            ORDER BY id ASC
            LIMIT ?
            """,
            (
                run_id,
                after_id,
                limit,
            ),
        ).fetchall()

    events = []

    for row in rows:
        events.append(
            {
                "id": row["id"],
                "run_id": row["run_id"],
                "timestamp": row["timestamp"],
                "stage": row["stage"],
                "event_type": row["event_type"],
                "message": row["message"],
                "details": json.loads(row["details"]),
            }
        )

    return events
