"""Control global y persistente del presupuesto de FitFamily."""

import sqlite3
import uuid

from dataclasses import dataclass
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import settings


DEFAULT_BUDGET_DB_PATH = settings.budget_db_path


class BudgetExceededError(RuntimeError):
    """Se ha alcanzado un límite de ejecución."""


@dataclass(frozen=True)
class BudgetLimits:
    max_calls: int
    max_tokens: int
    max_cost: float


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_run_id(run_id: str) -> None:
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("run_id no puede estar vacío.")


def _validate_nonnegative_number(
    name: str,
    value: int | float,
) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} debe ser numérico.")

    if value < 0 or value != value or value == float("inf"):
        raise ValueError(f"{name} debe ser finito y no negativo.")


def _get_limits(
    limits: BudgetLimits | None = None,
) -> BudgetLimits:
    if limits is None:
        limits = BudgetLimits(
            max_calls=settings.max_calls,
            max_tokens=settings.max_tokens,
            max_cost=settings.max_cost_usd,
        )

    if (
        type(limits.max_calls) is not int
        or type(limits.max_tokens) is not int
        or limits.max_calls < 1
        or limits.max_tokens < 1
        or limits.max_cost < 0
    ):
        raise ValueError("Los límites de presupuesto no son válidos.")

    return limits


def _connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(
        path,
        timeout=15,
    )

    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA busy_timeout=15000")

    return connection


def _initialize_db(db_path: str | Path) -> None:
    with closing(_connect(db_path)) as connection, connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS budget_entries (
                reservation_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                call_type TEXT NOT NULL,

                reserved_tokens INTEGER NOT NULL,
                reserved_cost REAL NOT NULL,

                actual_tokens INTEGER,
                actual_cost REAL,

                status TEXT NOT NULL,
                cost_is_estimate INTEGER NOT NULL DEFAULT 0,

                created_at TEXT NOT NULL,
                completed_at TEXT
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_budget_run
            ON budget_entries(run_id)
            """
        )


def _get_totals(
    connection: sqlite3.Connection,
    run_id: str,
) -> dict[str, Any]:
    row = connection.execute(
        """
        SELECT
            COUNT(*) AS calls,

            COALESCE(
                SUM(
                    CASE
                        WHEN actual_tokens IS NOT NULL
                        THEN actual_tokens
                        ELSE reserved_tokens
                    END
                ), 0
            ) AS tokens,

            COALESCE(
                SUM(
                    CASE
                        WHEN actual_cost IS NOT NULL
                        THEN actual_cost
                        ELSE reserved_cost
                    END
                ), 0
            ) AS cost,

            SUM(
                CASE WHEN status = 'reserved'
                THEN 1 ELSE 0 END
            ) AS pending_calls

        FROM budget_entries
        WHERE run_id = ?
        """,
        (run_id,),
    ).fetchone()

    return {
        "calls": row["calls"],
        "tokens": row["tokens"],
        "cost": float(row["cost"]),
        "pending_calls": row["pending_calls"] or 0,
    }


def _calculate_status(
    totals: dict[str, Any],
    limits: BudgetLimits,
) -> dict[str, Any]:
    reasons = []

    if totals["calls"] >= limits.max_calls:
        reasons.append("max_calls")

    if totals["tokens"] >= limits.max_tokens:
        reasons.append("max_tokens")

    if totals["cost"] >= limits.max_cost:
        reasons.append("max_cost")

    return {
        **totals,
        "limits": {
            "max_calls": limits.max_calls,
            "max_tokens": limits.max_tokens,
            "max_cost": limits.max_cost,
        },
        "remaining_calls": max(
            0, limits.max_calls - totals["calls"]
        ),
        "remaining_tokens": max(
            0, limits.max_tokens - totals["tokens"]
        ),
        "remaining_cost": max(
            0.0, limits.max_cost - totals["cost"]
        ),
        "exceeded": bool(reasons),
        "reasons": reasons,
    }


def check_limits(
    run_id: str,
    limits: BudgetLimits | None = None,
    db_path: str | Path = DEFAULT_BUDGET_DB_PATH,
) -> dict[str, Any]:
    """Consulta el consumo y comprueba los límites de una ejecución."""

    _validate_run_id(run_id)
    limits = _get_limits(limits)

    _initialize_db(db_path)

    with closing(_connect(db_path)) as connection, connection:
        totals = _get_totals(connection, run_id)

    return _calculate_status(totals, limits)


def reserve_call_budget(
    run_id: str,
    estimated_tokens: int,
    estimated_cost: float,
    call_type: str,
    limits: BudgetLimits | None = None,
    db_path: str | Path = DEFAULT_BUDGET_DB_PATH,
    reservation_id: str | None = None,
) -> dict[str, Any]:
    """
    Reserva presupuesto antes de ejecutar una llamada externa.

    estimated_tokens debe incluir el consumo de entrada conocido
    y la salida máxima prevista.

    estimated_cost debe ser una estimación conservadora en USD.
    """

    _validate_run_id(run_id)
    _validate_nonnegative_number(
        "estimated_tokens", estimated_tokens
    )
    _validate_nonnegative_number(
        "estimated_cost", estimated_cost
    )

    if type(estimated_tokens) is not int:
        raise ValueError("estimated_tokens debe ser entero.")

    if not isinstance(call_type, str) or not call_type.strip():
        raise ValueError("call_type no puede estar vacío.")

    limits = _get_limits(limits)

    if reservation_id is None:
        reservation_id = str(uuid.uuid4())

    _initialize_db(db_path)

    with closing(_connect(db_path)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")

        # Evita duplicar una reserva al repetir una operación.
        existing = connection.execute(
            """
            SELECT *
            FROM budget_entries
            WHERE reservation_id = ?
            """,
            (reservation_id,),
        ).fetchone()

        if existing is not None:
            if existing["run_id"] != run_id:
                raise ValueError(
                    "La reserva pertenece a otra ejecución."
                )

            return {
                "reservation_id": reservation_id,
                "run_id": run_id,
                "status": existing["status"],
                "duplicate": True,
            }

        totals = _get_totals(connection, run_id)
        current = _calculate_status(totals, limits)

        if current["exceeded"]:
            raise BudgetExceededError(
                f"Presupuesto agotado: {current['reasons']}"
            )

        projected_calls = totals["calls"] + 1
        projected_tokens = (
            totals["tokens"] + estimated_tokens
        )
        projected_cost = (
            totals["cost"] + estimated_cost
        )

        if projected_calls > limits.max_calls:
            raise BudgetExceededError(
                "La reserva superaría el límite de llamadas."
            )

        if projected_tokens > limits.max_tokens:
            raise BudgetExceededError(
                "La reserva superaría el límite de tokens."
            )

        if projected_cost > limits.max_cost:
            raise BudgetExceededError(
                "La reserva superaría el límite de coste."
            )

        connection.execute(
            """
            INSERT INTO budget_entries (
                reservation_id,
                run_id,
                call_type,
                reserved_tokens,
                reserved_cost,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, 'reserved', ?)
            """,
            (
                reservation_id,
                run_id,
                call_type,
                estimated_tokens,
                estimated_cost,
                _now(),
            ),
        )

    return {
        "reservation_id": reservation_id,
        "run_id": run_id,
        "call_type": call_type,
        "reserved_tokens": estimated_tokens,
        "reserved_cost": estimated_cost,
        "status": "reserved",
        "duplicate": False,
    }


def record_usage(
    run_id: str,
    reservation_id: str,
    actual_tokens: int | None = None,
    actual_cost: float | None = None,
    success: bool = True,
    db_path: str | Path = DEFAULT_BUDGET_DB_PATH,
) -> dict[str, Any]:
    """
    Registra el consumo de una llamada previamente reservada.

    Si el proveedor no informa del consumo real, se conserva
    la reserva como estimación, sin presentarla como consumo real.
    """

    _validate_run_id(run_id)

    if not isinstance(reservation_id, str) or not reservation_id:
        raise ValueError("reservation_id no puede estar vacío.")

    if actual_tokens is not None:
        _validate_nonnegative_number(
            "actual_tokens", actual_tokens
        )

        if type(actual_tokens) is not int:
            raise ValueError("actual_tokens debe ser entero.")

    if actual_cost is not None:
        _validate_nonnegative_number(
            "actual_cost", actual_cost
        )

    if type(success) is not bool:
        raise ValueError("success debe ser booleano.")

    _initialize_db(db_path)

    with closing(_connect(db_path)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")

        entry = connection.execute(
            """
            SELECT *
            FROM budget_entries
            WHERE reservation_id = ? AND run_id = ?
            """,
            (reservation_id, run_id),
        ).fetchone()

        if entry is None:
            raise ValueError(
                "No existe la reserva para esta ejecución."
            )

        if entry["status"] != "reserved":
            raise ValueError(
                "La reserva ya ha sido contabilizada."
            )

        # Si no conocemos el consumo real, mantenemos la estimación.
        tokens = (
            actual_tokens
            if actual_tokens is not None
            else entry["reserved_tokens"]
        )

        cost = (
            actual_cost
            if actual_cost is not None
            else entry["reserved_cost"]
        )

        cost_is_estimate = actual_cost is None

        status = "completed" if success else "failed"

        connection.execute(
            """
            UPDATE budget_entries
            SET
                actual_tokens = ?,
                actual_cost = ?,
                cost_is_estimate = ?,
                status = ?,
                completed_at = ?
            WHERE reservation_id = ?
            """,
            (
                tokens,
                cost,
                int(cost_is_estimate),
                status,
                _now(),
                reservation_id,
            ),
        )

        totals = _get_totals(connection, run_id)

    return {
        "reservation_id": reservation_id,
        "run_id": run_id,
        "status": status,
        "actual_tokens": tokens,
        "actual_cost": cost,
        "cost_is_estimate": cost_is_estimate,
        "success": success,
        "totals": totals,
    }
