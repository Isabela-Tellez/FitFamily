"""Configuración centralizada de FitFamily."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Configuración inmutable de la aplicación."""

    # Directorios
    data_dir: Path
    output_dir: Path

    # Persistencia
    checkpoints_db_path: Path
    events_db_path: Path
    budget_db_path: Path
    tracking_csv_path: Path

    # Workflow
    max_revisions: int
    max_automatic_retries: int
    tool_timeout_seconds: int

    # Presupuesto global
    max_calls: int
    max_tokens: int
    max_cost_usd: float

    # Aplicación
    app_title: str
    environment: str


def _read_int(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name)

    if raw is None:
        return default

    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} debe ser un entero.") from exc

    if value < minimum:
        raise ValueError(f"{name} debe ser >= {minimum}.")

    return value


def _read_float(name: str, default: float, minimum: float = 0.0) -> float:
    raw = os.getenv(name)

    if raw is None:
        return default

    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} debe ser numérico.") from exc

    if value < minimum or value != value or value == float("inf"):
        raise ValueError(f"{name} debe ser un número válido.")

    return value


def load_settings() -> Settings:
    """Carga y valida la configuración desde variables de entorno."""

    data_dir = Path(
        os.getenv("FITFAMILY_DATA_DIR", "data")
    )

    output_dir = Path(
        os.getenv("FITFAMILY_OUTPUT_DIR", "outputs/reports")
    )

    return Settings(
        data_dir=data_dir,
        output_dir=output_dir,

        checkpoints_db_path=Path(
            os.getenv(
                "FITFAMILY_CHECKPOINTS_DB",
                str(data_dir / "checkpoints.sqlite"),
            )
        ),

        events_db_path=Path(
            os.getenv(
                "FITFAMILY_EVENTS_DB",
                str(data_dir / "fitfamily_events.sqlite"),
            )
        ),

        budget_db_path=Path(
            os.getenv(
                "FITFAMILY_BUDGET_DB",
                str(data_dir / "budget.sqlite"),
            )
        ),

        tracking_csv_path=Path(
            os.getenv(
                "FITFAMILY_TRACKING_CSV",
                "outputs/tracking.csv",
            )
        ),

        max_revisions=_read_int(
            "FITFAMILY_MAX_REVISIONS", 2, 0
        ),

        max_automatic_retries=_read_int(
            "FITFAMILY_MAX_AUTOMATIC_RETRIES", 1, 0
        ),

        tool_timeout_seconds=_read_int(
            "FITFAMILY_TOOL_TIMEOUT_SECONDS", 60
        ),

        # Límites iniciales provisionales.
        max_calls=_read_int(
            "FITFAMILY_MAX_CALLS", 50
        ),

        max_tokens=_read_int(
            "FITFAMILY_MAX_TOKENS", 100_000
        ),

        max_cost_usd=_read_float(
            "FITFAMILY_MAX_COST_USD", 5.0
        ),

        app_title=os.getenv(
            "FITFAMILY_APP_TITLE",
            "FitFamily | Investigación y viabilidad",
        ),

        environment=os.getenv(
            "FITFAMILY_ENVIRONMENT",
            "development",
        ),
    )


settings = load_settings()
