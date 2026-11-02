"""
Estado compartido de las investigaciones de FitFamily.

Define los datos que LangGraph comparte entre los agentes y las etapas
del workflow, incluida la aprobación humana, la persistencia
y la exportación controlada de informes.
"""

from datetime import datetime, timezone
from operator import add
from typing import Annotated, Any, Literal, TypedDict


# ============================================================
# TIPOS DEL WORKFLOW
# ============================================================

RunStatus = Literal[
    "running",
    "awaiting_approval",
    "completed",
    "rejected",
    "budget_exceeded",
    "insufficient_evidence",
    "failed",
]

ApprovalDecision = Literal[
    "approved",
    "rejected",
]

DeliveryStatus = Literal[
    "not_started",
    "partial",
    "completed",
    "failed",
]


# ============================================================
# ESTADO COMPARTIDO
# ============================================================

class ResearchState(TypedDict, total=False):
    """
    Estado compartido y recuperable de una investigación.

    LangGraph utiliza este estado para comunicar información
    entre nodos y conservarla mediante un checkpointer.

    Los campos events y errors utilizan el reductor add:
    cada nodo debe devolver únicamente los elementos nuevos.
    """

    # --------------------------------------------------------
    # 1. IDENTIDAD Y ENCARGO
    # --------------------------------------------------------

    run_id: str
    brief: dict[str, Any]

    created_at: str
    updated_at: str

    # --------------------------------------------------------
    # 2. RESULTADOS DEL PROCESO
    # --------------------------------------------------------

    research_result: Any
    analysis_result: Any
    report_draft: Any
    review_result: Any

    # --------------------------------------------------------
    # 3. CONTROL DE VERSIONES DEL INFORME
    # --------------------------------------------------------

    report_version_id: str | None
    approved_version_id: str | None

    # --------------------------------------------------------
    # 4. APROBACIÓN HUMANA
    # --------------------------------------------------------

    approval_decision: ApprovalDecision | None
    approval_record: dict[str, Any] | None
    approved_at: str | None
    authorized_actions: list[str]

    # --------------------------------------------------------
    # 5. CONTROL DE EJECUCIÓN
    # --------------------------------------------------------

    status: RunStatus
    current_stage: str
    pending_tasks: list[str]
    stop_reason: str | None

    # --------------------------------------------------------
    # 6. EVENTOS Y ERRORES
    # --------------------------------------------------------

    events: Annotated[list[dict[str, Any]], add]
    errors: Annotated[list[dict[str, Any]], add]

    # --------------------------------------------------------
    # 7. CONSUMO Y PRESUPUESTO
    # --------------------------------------------------------

    usage: dict[str, Any]
    budget: dict[str, Any]

    # --------------------------------------------------------
    # 8. EXPORTACIÓN Y ENTREGA
    # --------------------------------------------------------

    delivery_result: dict[str, Any] | None
    delivery_status: DeliveryStatus
    export_paths: list[str]

    # Configuración de entrega.
    delivery_output_dir: str
    delivery_csv_path: str


# ============================================================
# CREACIÓN DEL ESTADO INICIAL
# ============================================================

def create_initial_state(
    run_id: str,
    brief: dict[str, Any],
) -> ResearchState:
    """
    Crea el estado inicial de una investigación.

    El run_id identifica la ejecución y debe mantenerse
    cuando se recupera o reanuda mediante LangGraph.

    La persistencia se gestiona mediante el checkpointer.
    """

    # --------------------------------------------------------
    # Validación del identificador
    # --------------------------------------------------------

    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError(
            "run_id debe ser una cadena no vacía."
        )

    # --------------------------------------------------------
    # Validación del encargo
    # --------------------------------------------------------

    if not isinstance(brief, dict) or not brief:
        raise ValueError(
            "brief debe ser un diccionario no vacío."
        )

    # --------------------------------------------------------
    # Marca temporal UTC
    # --------------------------------------------------------

    now = datetime.now(timezone.utc).isoformat()

    # --------------------------------------------------------
    # Estado inicial
    # --------------------------------------------------------

    return {
        # Identidad.
        "run_id": run_id,
        "brief": brief,
        "created_at": now,
        "updated_at": now,

        # Resultados.
        "research_result": None,
        "analysis_result": None,
        "report_draft": None,
        "review_result": None,

        # Versionado.
        "report_version_id": None,
        "approved_version_id": None,

        # Aprobación.
        "approval_decision": None,
        "approval_record": None,
        "authorized_actions": [],
        "approved_at": None,

        # Ejecución.
        "status": "running",
        "current_stage": "research",
        "pending_tasks": [],

        # Eventos y errores.
        "events": [],
        "errors": [],

        # Consumo.
        "usage": {
            "calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost": 0.0,
            "estimated_cost": 0.0,
        },

        # Presupuesto.
        "budget": {},

        # Entrega.
        "export_paths": [],
        "delivery_result": None,
        "delivery_status": "not_started",

        # Configuración de entrega.
        "delivery_output_dir": "outputs/reports",
        "delivery_csv_path": "outputs/tracking.csv",

        # Control de interrupciones.
        "stop_reason": None,
    }
